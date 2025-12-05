"""WebSocket API endpoints for wscat command."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import json

from src.services.ws_service import ws_service
from websockets.exceptions import WebSocketException


router = APIRouter(prefix="/ws", tags=["websocket"])


# Request/Response Models for API
class ConnectWSRequestModel(BaseModel):
    """Request model for connecting to WebSocket."""
    url: str = Field(..., description="WebSocket URL (ws:// or wss://)")
    headers: List[str] = Field(default_factory=list, description="Custom headers")
    protocol: Optional[str] = Field(None, description="WebSocket subprotocol")


class WSConnectionResponseModel(BaseModel):
    """Response model for WebSocket connection."""
    connection_id: str
    url: str
    connected: bool
    created_at: str
    protocol: Optional[str] = None


class SendMessageRequestModel(BaseModel):
    """Request model for sending WebSocket message."""
    connection_id: str = Field(..., description="Connection ID")
    message: str = Field(..., description="Message to send")


class WSMessageModel(BaseModel):
    """Model for WebSocket message."""
    type: str = Field(..., description="Message type: sent, received, error, status")
    message: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")


@router.post("/connect", response_model=WSConnectionResponseModel)
async def connect_websocket(request_data: ConnectWSRequestModel):
    """
    Connect to a WebSocket server.

    Args:
        request_data: WebSocket connection details

    Returns:
        Connection information with connection_id

    Raises:
        HTTPException: If connection fails
    """
    try:
        # Convert headers list to dict
        headers_dict = {}
        for header in request_data.headers:
            if ':' in header:
                key, value = header.split(':', 1)
                headers_dict[key.strip()] = value.strip()

        # Connect to WebSocket
        connection_id = await ws_service.connect(
            url=request_data.url,
            headers=request_data.headers,
            protocol=request_data.protocol
        )

        # Get connection status
        status = ws_service.get_connection_status(connection_id)
        if not status:
            raise HTTPException(status_code=500, detail="Failed to get connection status")

        return WSConnectionResponseModel(
            connection_id=status["connection_id"],
            url=status["url"],
            connected=status["connected"],
            created_at=status["created_at"],
            protocol=status["protocol"]
        )

    except WebSocketException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.post("/disconnect")
async def disconnect_websocket(connection_id: str):
    """
    Disconnect from a WebSocket server.

    Args:
        connection_id: The connection ID to disconnect

    Returns:
        Success status

    Raises:
        HTTPException: If disconnection fails
    """
    try:
        success = await ws_service.disconnect(connection_id)
        if not success:
            raise HTTPException(status_code=404, detail="Connection not found")

        return {"success": True, "message": "Disconnected successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnection failed: {str(e)}")


@router.post("/send")
async def send_message(request_data: SendMessageRequestModel):
    """
    Send a message through a WebSocket connection.

    Args:
        request_data: Connection ID and message

    Returns:
        Success status

    Raises:
        HTTPException: If send fails
    """
    try:
        success = await ws_service.send_message(
            connection_id=request_data.connection_id,
            message=request_data.message
        )

        return {
            "success": True,
            "message": "Message sent successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

    except WebSocketException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}")


@router.get("/status/{connection_id}")
async def get_connection_status(connection_id: str):
    """
    Get connection status information.

    Args:
        connection_id: The connection ID

    Returns:
        Connection status information

    Raises:
        HTTPException: If connection not found
    """
    status = ws_service.get_connection_status(connection_id)
    if not status:
        raise HTTPException(status_code=404, detail="Connection not found")

    return status


@router.websocket("/stream/{connection_id}")
async def websocket_stream(websocket: WebSocket, connection_id: str):
    """
    WebSocket endpoint for real-time bidirectional communication.

    This creates a WebSocket connection between the frontend and backend,
    which proxies messages to/from the external WebSocket server.

    Args:
        websocket: FastAPI WebSocket connection
        connection_id: The external WebSocket connection ID
    """
    await websocket.accept()

    try:
        # Check if connection exists
        status = ws_service.get_connection_status(connection_id)
        if not status or not status["connected"]:
            await websocket.send_json({
                "type": "error",
                "message": "Connection not found or not connected",
                "timestamp": datetime.utcnow().isoformat()
            })
            await websocket.close()
            return

        # Send connected status
        await websocket.send_json({
            "type": "status",
            "message": "Connected to stream",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Create tasks for bidirectional communication
        async def receive_from_frontend():
            """Receive messages from frontend and send to external WebSocket."""
            try:
                while True:
                    data = await websocket.receive_text()

                    # Parse message
                    try:
                        message_data = json.loads(data)
                        if message_data.get("type") == "message":
                            message = message_data.get("message", "")

                            # Send to external WebSocket
                            await ws_service.send_message(connection_id, message)

                            # Echo back confirmation
                            await websocket.send_json({
                                "type": "sent",
                                "message": message,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    except json.JSONDecodeError:
                        # If not JSON, treat as plain text message
                        await ws_service.send_message(connection_id, data)
                        await websocket.send_json({
                            "type": "sent",
                            "message": data,
                            "timestamp": datetime.utcnow().isoformat()
                        })

            except WebSocketDisconnect:
                pass
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

        async def send_to_frontend():
            """Receive messages from external WebSocket and send to frontend."""
            try:
                while True:
                    # Check if connection is still active
                    status = ws_service.get_connection_status(connection_id)
                    if not status or not status["connected"]:
                        await websocket.send_json({
                            "type": "status",
                            "message": "External connection closed",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        break

                    # Try to receive message from external WebSocket
                    message = await ws_service.receive_message(connection_id, timeout=0.5)
                    if message:
                        await websocket.send_json({
                            "type": "received",
                            "message": message,
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    # Small delay to prevent busy loop
                    await asyncio.sleep(0.01)

            except WebSocketDisconnect:
                pass
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })

        # Run both tasks concurrently
        receive_task = asyncio.create_task(receive_from_frontend())
        send_task = asyncio.create_task(send_to_frontend())

        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [receive_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
