"""SQL query REST API endpoints.

This module provides HTTP endpoints for sqlcat functionality including:
- Database connection management (SQLite, PostgreSQL)
- Schema introspection
- Query execution with pagination
- Query result visualization
- Exporting query results (CSV, JSON, Excel)

T034: Implementation of SQL API endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile

from src.models.database import (
    DatabaseConnection,
    DatabaseType,
    TableSchema,
    QueryResult,
    QueryHistory
)
from src.services.sql_service import SQLService
from src.utils.security import SecurityValidator  # T059: Security validation

# Initialize router
router = APIRouter(prefix="/api/sql", tags=["SQL"])

# Service instance (stateful for connection management)
sql_service = SQLService()


# Pydantic models for request/response validation
class ConnectDatabaseRequest(BaseModel):
    """Request model for database connection."""
    db_type: str = Field(..., description="Database type: sqlite or postgresql")
    connection_string: str = Field(..., description="Database connection string")
    display_name: Optional[str] = Field(None, description="User-friendly connection name")


class ConnectDatabaseResponse(BaseModel):
    """Response model for database connection."""
    is_connected: bool
    display_name: str
    masked_connection_string: str
    error_message: Optional[str] = None
    table_count: int = 0


class SchemaResponse(BaseModel):
    """Response model for database schema."""
    tables: List[Dict[str, Any]]


class ExecuteQueryRequest(BaseModel):
    """Request model for query execution."""
    connection_string: str = Field(..., description="Database connection string")
    db_type: str = Field(..., description="Database type: sqlite or postgresql")
    query: str = Field(..., description="SQL query to execute")
    offset: int = Field(0, description="Row offset for pagination", ge=0)
    limit: int = Field(1000, description="Maximum rows to return", ge=1, le=10000)


class ExecuteQueryResponse(BaseModel):
    """Response model for query execution."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float
    offset: int
    limit: int
    has_more: bool


class ExportQueryRequest(BaseModel):
    """Request model for query result export."""
    connection_string: str = Field(..., description="Database connection string")
    db_type: str = Field(..., description="Database type: sqlite or postgresql")
    query: str = Field(..., description="SQL query to execute")
    format: str = Field("csv", description="Export format: csv, json, or xlsx")


@router.post("/connect", response_model=ConnectDatabaseResponse)
async def connect_database(request: ConnectDatabaseRequest):
    """Connect to a database and retrieve schema information.

    Args:
        request: ConnectDatabaseRequest with connection details

    Returns:
        ConnectDatabaseResponse with connection status and schema summary

    Raises:
        HTTPException: If database type is invalid or connection fails
    """
    try:
        # Validate database type
        try:
            db_type = DatabaseType(request.db_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid database type: {request.db_type}. Must be 'sqlite' or 'postgresql'"
            )

        # Create database connection object
        db_connection = DatabaseConnection(
            db_type=db_type,
            connection_string=request.connection_string,
            display_name=request.display_name
        )

        # Connect and introspect schema
        db_connection = await sql_service.connect_database(db_connection)

        return ConnectDatabaseResponse(
            is_connected=db_connection.is_connected,
            display_name=db_connection.display_name or "Database",
            masked_connection_string=db_connection.masked_connection_string,
            error_message=db_connection.error_message,
            table_count=len(db_connection.tables)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to database: {str(e)}"
        )


@router.post("/schema", response_model=SchemaResponse)
async def get_database_schema(request: ConnectDatabaseRequest):
    """Get database schema (tables and columns).

    Args:
        request: ConnectDatabaseRequest with connection details

    Returns:
        SchemaResponse with table and column metadata

    Raises:
        HTTPException: If connection or schema introspection fails
    """
    try:
        # Validate database type
        try:
            db_type = DatabaseType(request.db_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid database type: {request.db_type}"
            )

        # Create and connect to database
        db_connection = DatabaseConnection(
            db_type=db_type,
            connection_string=request.connection_string,
            display_name=request.display_name
        )

        db_connection = await sql_service.connect_database(db_connection)

        if not db_connection.is_connected:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=db_connection.error_message or "Failed to connect to database"
            )

        # Convert tables to dict format
        tables_dict = []
        for table in db_connection.tables:
            columns_dict = [
                {
                    "name": col.name,
                    "data_type": col.data_type,
                    "nullable": col.nullable,
                    "primary_key": col.primary_key,
                    "default_value": col.default_value
                }
                for col in table.columns
            ]

            tables_dict.append({
                "name": table.name,
                "columns": columns_dict,
                "row_count": table.row_count,
                "indexes": table.indexes
            })

        return SchemaResponse(tables=tables_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database schema: {str(e)}"
        )


@router.post("/query", response_model=ExecuteQueryResponse)
async def execute_query(request: ExecuteQueryRequest):
    """Execute SQL query with pagination.

    Args:
        request: ExecuteQueryRequest with query and connection details

    Returns:
        ExecuteQueryResponse with query results

    Raises:
        HTTPException: If query execution fails
    """
    try:
        # Validate database type
        try:
            db_type = DatabaseType(request.db_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid database type: {request.db_type}"
            )

        # T059: Security validation - validate query
        try:
            SecurityValidator.validate_sql_query(request.query, allow_writes=False)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query validation failed: {str(e)}"
            )

        # T059: Security validation - validate connection string
        try:
            SecurityValidator.validate_connection_string(request.connection_string)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Connection string validation failed: {str(e)}"
            )

        # Create database connection
        db_connection = DatabaseConnection(
            db_type=db_type,
            connection_string=request.connection_string
        )

        # Connect to database
        db_connection = await sql_service.connect_database(db_connection)

        if not db_connection.is_connected:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=db_connection.error_message or "Failed to connect to database"
            )

        # Execute query
        result = await sql_service.execute_query(
            db_connection,
            request.query,
            offset=request.offset,
            limit=request.limit
        )

        return ExecuteQueryResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            execution_time_ms=result.execution_time_ms,
            offset=result.offset,
            limit=result.limit,
            has_more=result.has_more
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}"
        )


@router.post("/export")
async def export_query_results(request: ExportQueryRequest):
    """Export query results to CSV, JSON, or Excel.

    Args:
        request: ExportQueryRequest with query and export format

    Returns:
        File download response with exported data

    Raises:
        HTTPException: If export fails
    """
    try:
        # Validate database type
        try:
            db_type = DatabaseType(request.db_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid database type: {request.db_type}"
            )

        # Validate export format
        valid_formats = ["csv", "json", "xlsx"]
        if request.format.lower() not in valid_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid export format: {request.format}. Must be one of: {', '.join(valid_formats)}"
            )

        # Create database connection
        db_connection = DatabaseConnection(
            db_type=db_type,
            connection_string=request.connection_string
        )

        # Connect and execute query
        db_connection = await sql_service.connect_database(db_connection)

        if not db_connection.is_connected:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=db_connection.error_message or "Failed to connect to database"
            )

        # Execute query (no pagination for export)
        result = await sql_service.execute_query(
            db_connection,
            request.query,
            offset=0,
            limit=10000  # Max export limit
        )

        # Export based on format
        if request.format.lower() == "xlsx":
            # Create temporary file for Excel export
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            file_path = await sql_service.export_results(
                result,
                format="xlsx",
                file_path=temp_file.name
            )

            return FileResponse(
                path=file_path,
                filename=f"query_results.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        elif request.format.lower() == "csv":
            csv_data = await sql_service.export_results(result, format="csv")
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=query_results.csv"}
            )

        else:  # json
            json_data = await sql_service.export_results(result, format="json")
            return Response(
                content=json_data,
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=query_results.json"}
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )
