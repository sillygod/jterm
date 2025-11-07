"""Log viewing REST API endpoints.

This module provides HTTP endpoints for logcat functionality including:
- Parsing log files (JSON, Apache, Nginx formats)
- Filtering and searching log entries
- Streaming real-time log updates
- Exporting logs in various formats

T015: Implementation of log API endpoints.
"""

import json
import aiofiles
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field

from src.models.log_entry import LogEntry, LogFilter, LogStatistics, LogLevel, LogFormat
from src.services.log_service import get_log_service

# Initialize router
router = APIRouter(prefix="/api/logs", tags=["Logs"])

# Get log service instance
log_service = get_log_service()


# Pydantic models for request/response validation
class ParseLogRequest(BaseModel):
    """Request model for log file parsing."""
    file_path: str = Field(..., description="Absolute filesystem path to log file")
    log_format: Optional[str] = Field(None, description="Log format (auto-detected if not specified)")
    max_lines: int = Field(1000, description="Maximum number of lines to parse", ge=1, le=100000)


class FilterLogRequest(BaseModel):
    """Request model for log filtering."""
    file_path: str = Field(..., description="Absolute filesystem path to log file")
    levels: Optional[List[str]] = Field(None, description="Filter by log levels")
    search_pattern: Optional[str] = Field(None, description="Regex search pattern")
    since: Optional[str] = Field(None, description="Start time (ISO 8601)")
    until: Optional[str] = Field(None, description="End time (ISO 8601)")
    source: Optional[str] = Field(None, description="Filter by log source")
    has_stack_trace: Optional[bool] = Field(None, description="Filter entries with stack traces")
    log_format: Optional[str] = Field(None, description="Log format (auto-detected if not specified)")
    max_lines: int = Field(1000, description="Maximum number of lines to return", ge=1, le=100000)


class ExportLogRequest(BaseModel):
    """Request model for log export."""
    file_path: str = Field(..., description="Absolute filesystem path to log file")
    format: str = Field("json", description="Export format: json or csv")
    levels: Optional[List[str]] = Field(None, description="Filter by log levels")
    search_pattern: Optional[str] = Field(None, description="Regex search pattern")
    since: Optional[str] = Field(None, description="Start time (ISO 8601)")
    until: Optional[str] = Field(None, description="End time (ISO 8601)")


class ParseLogResponse(BaseModel):
    """Response model for parsed logs."""
    entries: List[dict]
    statistics: dict
    detected_format: str
    total_lines_processed: int


@router.post("/parse", response_model=ParseLogResponse)
async def parse_log_file(request: ParseLogRequest):
    """Parse and format log file with auto-detection.

    Args:
        request: ParseLogRequest with file path and options

    Returns:
        ParseLogResponse with parsed entries and statistics

    Raises:
        HTTPException: If file not found or parsing fails
    """
    try:
        # Determine log format
        log_format = None
        if request.log_format and request.log_format.lower() != "auto":
            try:
                log_format = LogFormat(request.log_format.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid log format: {request.log_format}"
                )

        # Parse log file
        entries = []
        count = 0
        async for entry in log_service.stream_file(request.file_path, log_format=log_format):
            entries.append(entry)
            count += 1
            if count >= request.max_lines:
                break

        if not entries:
            return ParseLogResponse(
                entries=[],
                statistics=LogStatistics().to_dict(),
                detected_format="unknown",
                total_lines_processed=0
            )

        # Calculate statistics
        stats = LogStatistics.from_entries(entries)

        # Detect format from first entry if not specified
        if log_format is None:
            # Re-detect from file
            async with aiofiles.open(request.file_path, 'r') as f:
                first_line = await f.readline()
                detected_format = log_service.detect_format(first_line)
        else:
            detected_format = log_format

        return ParseLogResponse(
            entries=[entry.to_dict() for entry in entries],
            statistics=stats.to_dict(),
            detected_format=detected_format.value,
            total_lines_processed=len(entries)
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_details = f"Failed to parse log file: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(error_details)  # Log to console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse log file: {type(e).__name__}: {str(e) or 'Unknown error'}"
        )


@router.post("/filter", response_model=ParseLogResponse)
async def filter_log_entries(request: FilterLogRequest):
    """Filter log entries based on criteria.

    Args:
        request: FilterLogRequest with file path and filter options

    Returns:
        ParseLogResponse with filtered entries and statistics

    Raises:
        HTTPException: If file not found or filtering fails
    """
    try:
        # Build filter
        levels = []
        if request.levels:
            for level_str in request.levels:
                try:
                    levels.append(LogLevel(level_str.upper()))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid log level: {level_str}"
                    )

        # Parse timestamps
        since = None
        if request.since:
            try:
                since = datetime.fromisoformat(request.since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid 'since' timestamp format"
                )

        until = None
        if request.until:
            try:
                until = datetime.fromisoformat(request.until.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid 'until' timestamp format"
                )

        log_filter = LogFilter(
            levels=levels,
            search_pattern=request.search_pattern,
            since=since,
            until=until,
            source=request.source,
            has_stack_trace=request.has_stack_trace
        )

        # Determine log format
        log_format = None
        if request.log_format and request.log_format.lower() != "auto":
            try:
                log_format = LogFormat(request.log_format.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid log format: {request.log_format}"
                )

        # Stream and filter
        entries = []
        count = 0
        async for entry in log_service.stream_file(request.file_path, log_format=log_format, log_filter=log_filter):
            entries.append(entry)
            count += 1
            if count >= request.max_lines:
                break

        # Calculate statistics
        stats = LogStatistics.from_entries(entries) if entries else LogStatistics()

        # Detect format
        if log_format is None:
            async with aiofiles.open(request.file_path, 'r') as f:
                first_line = await f.readline()
                detected_format = log_service.detect_format(first_line)
        else:
            detected_format = log_format

        return ParseLogResponse(
            entries=[entry.to_dict() for entry in entries],
            statistics=stats.to_dict(),
            detected_format=detected_format.value,
            total_lines_processed=len(entries)
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter log entries: {str(e)}"
        )


@router.get("/stream")
async def stream_log_file(
    file_path: str = Query(..., description="Absolute filesystem path to log file"),
    log_format: Optional[str] = Query(None, description="Log format (auto-detected if not specified)"),
    follow: bool = Query(False, description="Follow file for new entries (tail -f mode)")
):
    """Stream log file with real-time updates.

    Args:
        file_path: Path to log file
        log_format: Optional log format
        follow: Whether to follow file for new entries

    Returns:
        StreamingResponse with log entries as NDJSON (newline-delimited JSON)

    Raises:
        HTTPException: If file not found
    """
    try:
        # Determine log format
        format_enum = None
        if log_format and log_format.lower() != "auto":
            try:
                format_enum = LogFormat(log_format.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid log format: {log_format}"
                )

        async def stream_generator():
            """Generate log entries as NDJSON."""
            async for entry in log_service.stream_file(file_path, log_format=format_enum):
                yield json.dumps(entry.to_dict()) + "\n"

            # TODO: Implement follow mode (tail -f) if requested
            # This would require file watching (e.g., watchdog library)

        return StreamingResponse(
            stream_generator(),
            media_type="application/x-ndjson",
            headers={
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-cache"
            }
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stream log file: {str(e)}"
        )


@router.post("/export")
async def export_log_file(request: ExportLogRequest):
    """Export filtered logs in various formats (CSV, JSON).

    Args:
        request: ExportLogRequest with file path, format, and filters

    Returns:
        Response with exported log data

    Raises:
        HTTPException: If export fails
    """
    try:
        # Build filter
        levels = []
        if request.levels:
            for level_str in request.levels:
                try:
                    levels.append(LogLevel(level_str.upper()))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid log level: {level_str}"
                    )

        # Parse timestamps
        since = None
        if request.since:
            since = datetime.fromisoformat(request.since.replace('Z', '+00:00'))

        until = None
        if request.until:
            until = datetime.fromisoformat(request.until.replace('Z', '+00:00'))

        log_filter = LogFilter(
            levels=levels,
            search_pattern=request.search_pattern,
            since=since,
            until=until
        ) if any([request.levels, request.search_pattern, request.since, request.until]) else None

        # Collect entries
        entries = []
        async for entry in log_service.stream_file(request.file_path, log_filter=log_filter):
            entries.append(entry)

        # Export based on format
        if request.format.lower() == "json":
            content = json.dumps([entry.to_dict() for entry in entries], indent=2)
            media_type = "application/json"
            filename = "logs.json"

        elif request.format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            if entries:
                # CSV headers
                fieldnames = ["timestamp", "level", "message", "source", "line_number"]
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for entry in entries:
                    writer.writerow({
                        "timestamp": entry.display_time,
                        "level": entry.level.value,
                        "message": entry.message,
                        "source": entry.source or "",
                        "line_number": entry.line_number
                    })

            content = output.getvalue()
            media_type = "text/csv"
            filename = "logs.csv"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {request.format}"
            )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export log file: {str(e)}"
        )
