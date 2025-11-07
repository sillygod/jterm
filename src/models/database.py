"""Database models for sqlcat command.

This module defines data structures for database connections, query execution,
and schema introspection supporting SQLite and PostgreSQL.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import re
import csv
import io
import json


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


@dataclass
class DatabaseConnection:
    """Database connection information."""
    db_type: DatabaseType
    connection_string: str
    display_name: Optional[str] = None

    # Connection state
    is_connected: bool = False
    error_message: Optional[str] = None

    # Schema metadata (populated after connection)
    tables: List['TableSchema'] = field(default_factory=list)

    @property
    def masked_connection_string(self) -> str:
        """Connection string with password masked."""
        # Mask password in postgresql://user:password@host/db
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', self.connection_string)
        return masked

    @classmethod
    def from_sqlite_path(cls, path: str) -> 'DatabaseConnection':
        """Create SQLite connection from file path."""
        return cls(
            db_type=DatabaseType.SQLITE,
            connection_string=f"sqlite:///{path}",
            display_name=path.split('/')[-1]
        )

    @classmethod
    def from_postgres_dsn(cls, dsn: str) -> 'DatabaseConnection':
        """Create PostgreSQL connection from DSN."""
        return cls(
            db_type=DatabaseType.POSTGRESQL,
            connection_string=dsn,
            display_name="PostgreSQL Database"
        )


@dataclass
class ColumnSchema:
    """Table column metadata."""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    default_value: Optional[str] = None


@dataclass
class TableSchema:
    """Table metadata."""
    name: str
    columns: List[ColumnSchema] = field(default_factory=list)
    row_count: Optional[int] = None
    indexes: List[str] = field(default_factory=list)

    @property
    def column_names(self) -> List[str]:
        """List of column names."""
        return [col.name for col in self.columns]

    @property
    def primary_keys(self) -> List[str]:
        """List of primary key columns."""
        return [col.name for col in self.columns if col.primary_key]


@dataclass
class QueryResult:
    """SQL query execution result."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time_ms: float

    # Pagination
    offset: int = 0
    limit: int = 1000
    has_more: bool = False

    # Query metadata
    query: str = ""
    explain_plan: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        """Check if result is empty."""
        return self.row_count == 0

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries."""
        return [
            {col: val for col, val in zip(self.columns, row)}
            for row in self.rows
        ]

    def to_csv(self) -> str:
        """Export as CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.columns)
        writer.writerows(self.rows)
        return output.getvalue()

    def to_json(self) -> str:
        """Export as JSON format."""
        return json.dumps(self.to_dict_list(), indent=2, default=str)


@dataclass
class QueryHistory:
    """Saved SQL query."""
    query: str
    timestamp: datetime
    execution_time_ms: float
    row_count: int
    success: bool = True
    error_message: Optional[str] = None

    # User annotations
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Human-readable name."""
        if self.name:
            return self.name
        # Generate from query (first 50 chars)
        return self.query[:50] + "..." if len(self.query) > 50 else self.query
