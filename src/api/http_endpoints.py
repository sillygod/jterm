"""HTTP API endpoints for curlcat command."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

from src.models.http_request import (
    HTTPRequest,
    HTTPResponse,
    HTTPMethod,
    AuthType,
    EnvironmentVariable,
    RequestHistory
)
from src.services.http_service import HTTPService


router = APIRouter(prefix="/http", tags=["http"])
http_service = HTTPService()


# Request/Response Models for API
class ExecuteHTTPRequestModel(BaseModel):
    """Request model for executing HTTP requests."""
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    url: str = Field(..., description="Target URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    body: Optional[str] = Field(None, description="Request body")
    auth_type: str = Field(default="none", description="Authentication type")
    auth_credentials: Optional[str] = Field(None, description="Authentication credentials")
    follow_redirects: bool = Field(default=True, description="Follow redirects")
    timeout_seconds: int = Field(default=30, description="Request timeout")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    proxy: Optional[str] = Field(None, description="Proxy URL (e.g., http://proxy.example.com:8080)")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")


class HTTPResponseModel(BaseModel):
    """Response model for HTTP requests."""
    status_code: int
    headers: Dict[str, str]
    body: str
    timing: Dict[str, float]
    redirect_chain: List[str]


class ExportCodeRequestModel(BaseModel):
    """Request model for exporting request as code."""
    request: ExecuteHTTPRequestModel
    language: str = Field(default="curl", description="Target language (curl, python, javascript)")


class EnvironmentVariableModel(BaseModel):
    """Model for environment variable."""
    name: str
    value: str
    description: Optional[str] = None


class RequestHistoryModel(BaseModel):
    """Model for request history entry."""
    request: ExecuteHTTPRequestModel
    response: Optional[HTTPResponseModel] = None
    timestamp: str
    success: bool = True
    error_message: Optional[str] = None
    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


@router.post("/execute", response_model=HTTPResponseModel)
async def execute_http_request(request_data: ExecuteHTTPRequestModel):
    """
    Execute an HTTP request and return response with timing.

    Args:
        request_data: HTTP request details

    Returns:
        HTTP response with status, headers, body, and timing

    Raises:
        HTTPException: If request execution fails
    """
    try:
        # Convert request model to HTTPRequest
        http_request = HTTPRequest(
            method=HTTPMethod(request_data.method.upper()),
            url=request_data.url,
            headers=request_data.headers,
            body=request_data.body,
            auth_type=AuthType(request_data.auth_type.lower()),
            auth_credentials=request_data.auth_credentials,
            follow_redirects=request_data.follow_redirects,
            timeout_seconds=request_data.timeout_seconds,
            verify_ssl=request_data.verify_ssl,
            proxy=request_data.proxy,
            environment=request_data.environment
        )

        # Execute request
        response = await http_service.execute_request(http_request)

        # Convert to response model
        return HTTPResponseModel(
            status_code=response.status_code,
            headers=response.headers,
            body=response.body,
            timing={
                "dns_lookup_ms": response.timing.dns_lookup_ms,
                "tcp_connect_ms": response.timing.tcp_connect_ms,
                "tls_handshake_ms": response.timing.tls_handshake_ms,
                "server_processing_ms": response.timing.server_processing_ms,
                "transfer_ms": response.timing.transfer_ms,
                "total_ms": response.timing.total_ms
            },
            redirect_chain=response.redirect_chain
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


@router.post("/export")
async def export_as_code(export_data: ExportCodeRequestModel):
    """
    Export HTTP request as code in various languages.

    Args:
        export_data: Request details and target language

    Returns:
        Code snippet as string

    Raises:
        HTTPException: If export fails
    """
    try:
        # Convert request model to HTTPRequest
        http_request = HTTPRequest(
            method=HTTPMethod(export_data.request.method.upper()),
            url=export_data.request.url,
            headers=export_data.request.headers,
            body=export_data.request.body,
            auth_type=AuthType(export_data.request.auth_type.lower()),
            auth_credentials=export_data.request.auth_credentials,
            follow_redirects=export_data.request.follow_redirects,
            timeout_seconds=export_data.request.timeout_seconds,
            verify_ssl=export_data.request.verify_ssl,
            proxy=export_data.request.proxy,
            environment=export_data.request.environment
        )

        # Export as code
        code = http_service.export_as_code(http_request, export_data.language)

        return {"code": code, "language": export_data.language}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/history")
async def get_request_history():
    """
    Get request history (stored in browser localStorage).

    Note: This endpoint returns an empty list as history is managed client-side.
    In a future implementation, this could return server-side stored history.

    Returns:
        Empty list (client manages history)
    """
    # History is stored in browser localStorage per spec
    # This endpoint is a placeholder for future server-side history
    return {"history": [], "message": "History is stored client-side in localStorage"}


@router.post("/environment/variables")
async def add_environment_variable(var: EnvironmentVariableModel):
    """
    Add or update an environment variable.

    Args:
        var: Environment variable details

    Returns:
        Success message

    Raises:
        HTTPException: If variable is invalid
    """
    try:
        env_var = EnvironmentVariable(
            name=var.name,
            value=var.value,
            description=var.description
        )
        http_service.add_environment_variable(env_var)
        return {"message": f"Environment variable '{var.name}' added successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add variable: {str(e)}")


@router.get("/environment/variables")
async def get_environment_variables():
    """
    Get all environment variables.

    Returns:
        Dictionary of variable name -> variable details
    """
    variables = http_service.get_all_environment_variables()
    return {
        "variables": {
            name: {
                "name": var.name,
                "value": var.value,
                "description": var.description
            }
            for name, var in variables.items()
        }
    }


@router.delete("/environment/variables/{name}")
async def remove_environment_variable(name: str):
    """
    Remove an environment variable.

    Args:
        name: Variable name to remove

    Returns:
        Success message

    Raises:
        HTTPException: If variable not found
    """
    success = http_service.remove_environment_variable(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Variable '{name}' not found")
    return {"message": f"Environment variable '{name}' removed successfully"}


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service status
    """
    return {"status": "healthy", "service": "http"}
