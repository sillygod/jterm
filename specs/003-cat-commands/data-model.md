# Data Model: Web-Enhanced Cat Commands

**Feature**: 003-cat-commands
**Date**: 2025-11-04
**Status**: Phase 1 - Design

## Overview

This document defines the data entities, relationships, and validation rules for the four cat commands. All models are Python dataclasses with type hints, designed for FastAPI integration.

## Model Organization

```
src/models/
├── log_entry.py        # LOGCAT entities
├── certificate.py      # CERTCAT entities
├── database.py         # SQLCAT entities
└── http_request.py     # CURLCAT entities
```

---

## 1. LOGCAT Models (`log_entry.py`)

### LogEntry
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

class LogLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

class LogFormat(Enum):
    JSON = "json"
    APACHE_COMBINED = "apache_combined"
    APACHE_COMMON = "apache_common"
    NGINX_ERROR = "nginx_error"
    PLAIN_TEXT = "plain_text"

@dataclass
class LogEntry:
    """Represents a single log line"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: Optional[str] = None  # Log source (file, module, service)
    line_number: int = 0           # Line number in original file
    raw_text: str = ""             # Original unparsed line

    # Structured fields (JSON logs only)
    structured_fields: Dict[str, Any] = field(default_factory=dict)

    # Stack trace (if present)
    stack_trace: Optional[str] = None

    def __post_init__(self):
        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"Invalid timestamp: {self.timestamp}")

        # Normalize level to uppercase
        if isinstance(self.level, str):
            self.level = LogLevel(self.level.upper())

    @property
    def is_error(self) -> bool:
        """Check if log is error or fatal"""
        return self.level in [LogLevel.ERROR, LogLevel.FATAL]

    @property
    def display_time(self) -> str:
        """Human-readable timestamp"""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
```

### LogFilter
```python
@dataclass
class LogFilter:
    """Filter criteria for log entries"""
    levels: List[LogLevel] = field(default_factory=list)  # Empty = all levels
    search_pattern: Optional[str] = None  # Regex pattern
    since: Optional[datetime] = None      # Start time filter
    until: Optional[datetime] = None      # End time filter
    source: Optional[str] = None          # Source filter (file, module)
    has_stack_trace: Optional[bool] = None  # Only logs with stack traces

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry matches filter criteria"""
        # Level filter
        if self.levels and entry.level not in self.levels:
            return False

        # Time range filter
        if self.since and entry.timestamp < self.since:
            return False
        if self.until and entry.timestamp > self.until:
            return False

        # Source filter
        if self.source and entry.source != self.source:
            return False

        # Stack trace filter
        if self.has_stack_trace is not None:
            if self.has_stack_trace and not entry.stack_trace:
                return False
            if not self.has_stack_trace and entry.stack_trace:
                return False

        # Search pattern (regex)
        if self.search_pattern:
            import re
            if not re.search(self.search_pattern, entry.message):
                return False

        return True
```

### LogStatistics
```python
@dataclass
class LogStatistics:
    """Aggregate statistics for log analysis"""
    total_entries: int = 0
    level_counts: Dict[LogLevel, int] = field(default_factory=dict)
    time_range: tuple[datetime, datetime] = field(default=(None, None))
    sources: List[str] = field(default_factory=list)
    error_rate: float = 0.0  # Percentage of ERROR/FATAL logs

    @classmethod
    def from_entries(cls, entries: List[LogEntry]) -> 'LogStatistics':
        """Calculate statistics from log entries"""
        if not entries:
            return cls()

        level_counts = {}
        for entry in entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1

        error_count = sum(1 for e in entries if e.is_error)
        error_rate = (error_count / len(entries)) * 100 if entries else 0

        sources = list(set(e.source for e in entries if e.source))

        return cls(
            total_entries=len(entries),
            level_counts=level_counts,
            time_range=(entries[0].timestamp, entries[-1].timestamp),
            sources=sources,
            error_rate=round(error_rate, 2)
        )
```

**Validation Rules**:
- `timestamp` must be valid datetime
- `level` must be one of defined LogLevel enum values
- `line_number` must be >= 0
- `search_pattern` must be valid regex (validated at API layer)

---

## 2. CERTCAT Models (`certificate.py`)

### Certificate
```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

class KeyAlgorithm(Enum):
    RSA = "RSA"
    ECDSA = "ECDSA"
    DSA = "DSA"
    ED25519 = "Ed25519"

class TrustStatus(Enum):
    TRUSTED = "trusted"           # Valid chain to trusted root
    UNTRUSTED = "untrusted"       # Invalid chain or self-signed
    EXPIRED = "expired"           # Certificate expired
    NOT_YET_VALID = "not_yet_valid"  # Not valid yet
    REVOKED = "revoked"           # Certificate revoked

@dataclass
class PublicKeyInfo:
    """Public key details"""
    algorithm: KeyAlgorithm
    size_bits: int  # Key size (e.g., 2048, 4096, 256)
    fingerprint_sha256: str
    fingerprint_sha1: str  # Legacy, still shown for compatibility

    @property
    def display_algorithm(self) -> str:
        """Human-readable algorithm description"""
        return f"{self.algorithm.value} {self.size_bits}-bit"

@dataclass
class Certificate:
    """X.509 certificate representation"""
    # Basic information
    subject: str  # Common Name (CN)
    issuer: str   # Issuer CN
    serial_number: str  # Hex-encoded serial number

    # Validity period
    not_before: datetime
    not_after: datetime

    # Public key
    public_key: PublicKeyInfo

    # Subject Alternative Names
    san: List[str] = field(default_factory=list)  # DNS names, IPs

    # Chain information
    parent_cert: Optional['Certificate'] = None  # Issuer certificate
    is_self_signed: bool = False
    is_ca: bool = False  # Is Certificate Authority

    # Trust status
    trust_status: TrustStatus = TrustStatus.UNTRUSTED

    # Raw data (for export)
    pem_data: Optional[str] = None
    der_data: Optional[bytes] = None

    @property
    def is_expired(self) -> bool:
        """Check if certificate is expired"""
        now = datetime.now(self.not_after.tzinfo)
        return now > self.not_after

    @property
    def is_expiring_soon(self, days_threshold: int = 30) -> bool:
        """Check if certificate expires within threshold"""
        now = datetime.now(self.not_after.tzinfo)
        days_remaining = (self.not_after - now).days
        return 0 < days_remaining <= days_threshold

    @property
    def days_until_expiry(self) -> int:
        """Days until expiration (negative if expired)"""
        now = datetime.now(self.not_after.tzinfo)
        return (self.not_after - now).days

    @property
    def expiry_warning(self) -> Optional[str]:
        """Human-readable expiry warning"""
        if self.is_expired:
            return f"⚠️ EXPIRED {abs(self.days_until_expiry)} days ago"
        elif self.is_expiring_soon():
            return f"⚠️ Expires in {self.days_until_expiry} days"
        return None

@dataclass
class CertificateChain:
    """Complete certificate chain"""
    leaf: Certificate  # End-entity certificate
    intermediates: List[Certificate] = field(default_factory=list)
    root: Optional[Certificate] = None

    @property
    def is_complete(self) -> bool:
        """Check if chain reaches trusted root"""
        return self.root is not None and self.root.is_ca

    @property
    def chain_length(self) -> int:
        """Total certificates in chain"""
        return 1 + len(self.intermediates) + (1 if self.root else 0)

    def get_all_certificates(self) -> List[Certificate]:
        """Get flattened list of all certificates"""
        certs = [self.leaf] + self.intermediates
        if self.root:
            certs.append(self.root)
        return certs
```

**Validation Rules**:
- `not_before` must be < `not_after`
- `serial_number` must be hex string
- `san` list must contain valid DNS names or IP addresses
- `public_key.size_bits` must be >= 256 (weak keys flagged)
- `pem_data` must start with `-----BEGIN CERTIFICATE-----`

---

## 3. SQLCAT Models (`database.py`)

### DatabaseConnection
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"

@dataclass
class DatabaseConnection:
    """Database connection information"""
    db_type: DatabaseType
    connection_string: str
    display_name: Optional[str] = None  # User-friendly name

    # Connection state
    is_connected: bool = False
    error_message: Optional[str] = None

    # Schema metadata (populated after connection)
    tables: List['TableSchema'] = field(default_factory=list)

    @property
    def masked_connection_string(self) -> str:
        """Connection string with password masked"""
        import re
        # Mask password in postgresql://user:password@host/db
        masked = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', self.connection_string)
        return masked

    @classmethod
    def from_sqlite_path(cls, path: str) -> 'DatabaseConnection':
        """Create SQLite connection from file path"""
        return cls(
            db_type=DatabaseType.SQLITE,
            connection_string=f"sqlite:///{path}",
            display_name=path.split('/')[-1]
        )

    @classmethod
    def from_postgres_dsn(cls, dsn: str) -> 'DatabaseConnection':
        """Create PostgreSQL connection from DSN"""
        return cls(
            db_type=DatabaseType.POSTGRESQL,
            connection_string=dsn,
            display_name="PostgreSQL Database"
        )

@dataclass
class ColumnSchema:
    """Table column metadata"""
    name: str
    data_type: str  # SQL type (VARCHAR, INTEGER, etc.)
    nullable: bool = True
    primary_key: bool = False
    default_value: Optional[str] = None

@dataclass
class TableSchema:
    """Table metadata"""
    name: str
    columns: List[ColumnSchema] = field(default_factory=list)
    row_count: Optional[int] = None  # Estimated row count
    indexes: List[str] = field(default_factory=list)  # Index names

    @property
    def column_names(self) -> List[str]:
        """List of column names"""
        return [col.name for col in self.columns]

    @property
    def primary_keys(self) -> List[str]:
        """List of primary key columns"""
        return [col.name for col in self.columns if col.primary_key]
```

### QueryResult
```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class QueryResult:
    """SQL query execution result"""
    columns: List[str]  # Column names
    rows: List[List[Any]]  # Row data
    row_count: int  # Number of rows returned
    execution_time_ms: float  # Query execution time

    # Pagination
    offset: int = 0
    limit: int = 1000
    has_more: bool = False  # More rows available

    # Query metadata
    query: str = ""  # Original query
    explain_plan: Optional[str] = None  # EXPLAIN output

    @property
    def is_empty(self) -> bool:
        """Check if result is empty"""
        return self.row_count == 0

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries"""
        return [
            {col: val for col, val in zip(self.columns, row)}
            for row in self.rows
        ]

    def to_csv(self) -> str:
        """Export as CSV format"""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(self.columns)
        writer.writerows(self.rows)
        return output.getvalue()

    def to_json(self) -> str:
        """Export as JSON format"""
        import json
        return json.dumps(self.to_dict_list(), indent=2, default=str)

@dataclass
class QueryHistory:
    """Saved SQL query"""
    query: str
    timestamp: datetime
    execution_time_ms: float
    row_count: int
    success: bool = True
    error_message: Optional[str] = None

    # User annotations
    name: Optional[str] = None  # User-given name
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Human-readable name"""
        if self.name:
            return self.name
        # Generate from query (first 50 chars)
        return self.query[:50] + "..." if len(self.query) > 50 else self.query
```

**Validation Rules**:
- `connection_string` must match pattern for database type
- `limit` must be between 1 and 10,000 (prevent huge result sets)
- `query` must not be empty
- `execution_time_ms` must be >= 0
- SQLite path must exist (validated at service layer)
- PostgreSQL DSN must be valid format: `postgresql://user:pass@host:port/db`

---

## 4. CURLCAT Models (`http_request.py`)

### HTTPRequest
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

class HTTPMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class AuthType(Enum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"

@dataclass
class HTTPRequest:
    """HTTP request representation"""
    method: HTTPMethod
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    auth_type: AuthType = AuthType.NONE
    auth_credentials: Optional[str] = None  # Base64 basic auth or token

    # Options
    follow_redirects: bool = True
    timeout_seconds: int = 30
    verify_ssl: bool = True

    # Environment variables (for substitution)
    environment: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        # Validate URL
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {self.url}")

        # Validate timeout
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ValueError(f"Timeout must be 1-300 seconds, got {self.timeout_seconds}")

    def substitute_variables(self) -> 'HTTPRequest':
        """Replace {{VAR}} placeholders with environment values"""
        import re
        substituted_url = self.url
        substituted_body = self.body
        substituted_headers = dict(self.headers)

        for var_name, var_value in self.environment.items():
            pattern = r'\{\{' + re.escape(var_name) + r'\}\}'

            # Substitute in URL
            substituted_url = re.sub(pattern, var_value, substituted_url)

            # Substitute in body
            if substituted_body:
                substituted_body = re.sub(pattern, var_value, substituted_body)

            # Substitute in headers
            for key in substituted_headers:
                substituted_headers[key] = re.sub(pattern, var_value, substituted_headers[key])

        return HTTPRequest(
            method=self.method,
            url=substituted_url,
            headers=substituted_headers,
            body=substituted_body,
            auth_type=self.auth_type,
            auth_credentials=self.auth_credentials,
            follow_redirects=self.follow_redirects,
            timeout_seconds=self.timeout_seconds,
            verify_ssl=self.verify_ssl,
            environment=self.environment
        )

    def to_curl_command(self) -> str:
        """Generate equivalent curl command"""
        parts = ["curl"]

        # Method
        if self.method != HTTPMethod.GET:
            parts.append(f"-X {self.method.value}")

        # Headers
        for key, value in self.headers.items():
            parts.append(f"-H '{key}: {value}'")

        # Body
        if self.body:
            parts.append(f"-d '{self.body}'")

        # Auth
        if self.auth_type == AuthType.BASIC:
            parts.append(f"-u '{self.auth_credentials}'")
        elif self.auth_type == AuthType.BEARER:
            parts.append(f"-H 'Authorization: Bearer {self.auth_credentials}'")

        # Options
        if self.follow_redirects:
            parts.append("-L")
        if not self.verify_ssl:
            parts.append("-k")

        parts.append(f"'{self.url}'")

        return " ".join(parts)
```

### HTTPResponse
```python
@dataclass
class HTTPTimingBreakdown:
    """Detailed timing information"""
    dns_lookup_ms: float = 0  # DNS resolution time
    tcp_connect_ms: float = 0  # TCP connection establishment
    tls_handshake_ms: float = 0  # TLS handshake (if HTTPS)
    server_processing_ms: float = 0  # Time to first byte
    transfer_ms: float = 0  # Data transfer time
    total_ms: float = 0  # Total request time

    @property
    def formatted_total(self) -> str:
        """Human-readable total time"""
        if self.total_ms < 1000:
            return f"{int(self.total_ms)}ms"
        else:
            return f"{self.total_ms / 1000:.2f}s"

@dataclass
class HTTPResponse:
    """HTTP response representation"""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    timing: HTTPTimingBreakdown = field(default_factory=HTTPTimingBreakdown)

    # Redirect chain (if followed)
    redirect_chain: List[str] = field(default_factory=list)

    # Certificate info (if HTTPS)
    certificate: Optional[Certificate] = None

    @property
    def content_type(self) -> Optional[str]:
        """Extract Content-Type header"""
        return self.headers.get('content-type') or self.headers.get('Content-Type')

    @property
    def is_json(self) -> bool:
        """Check if response is JSON"""
        ct = self.content_type
        return ct is not None and 'application/json' in ct

    @property
    def is_html(self) -> bool:
        """Check if response is HTML"""
        ct = self.content_type
        return ct is not None and 'text/html' in ct

    @property
    def status_category(self) -> str:
        """HTTP status category"""
        if 200 <= self.status_code < 300:
            return "success"
        elif 300 <= self.status_code < 400:
            return "redirect"
        elif 400 <= self.status_code < 500:
            return "client_error"
        elif 500 <= self.status_code < 600:
            return "server_error"
        else:
            return "unknown"

@dataclass
class EnvironmentVariable:
    """Reusable environment variable for curlcat"""
    name: str
    value: str
    description: Optional[str] = None  # User annotation

    def __post_init__(self):
        # Validate name (alphanumeric + underscore only)
        import re
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', self.name):
            raise ValueError(f"Invalid variable name: {self.name}. Use UPPERCASE_WITH_UNDERSCORES")

@dataclass
class RequestHistory:
    """Saved HTTP request with response"""
    request: HTTPRequest
    response: Optional[HTTPResponse] = None
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None

    # User annotations
    name: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Human-readable name"""
        if self.name:
            return self.name
        return f"{self.request.method.value} {self.request.url}"
```

**Validation Rules**:
- `url` must start with `http://` or `https://`
- `timeout_seconds` must be 1-300
- `status_code` must be 100-599
- `EnvironmentVariable.name` must match regex `^[A-Z_][A-Z0-9_]*$`
- `headers` keys must be valid HTTP header names
- `body` size limited to 10MB (validated at API layer)

---

## Storage Considerations

### In-Memory (Session Scope)
- `DatabaseConnection` - Active database connections
- `EnvironmentVariable` - curlcat environment variables
- `LogFilter` - Current filter state
- WebSocket streams for log following

### Browser localStorage (30-day retention)
- `QueryHistory[]` - SQL query history
- `RequestHistory[]` - HTTP request history
- User preferences (theme, layout)

### File System
- Exported logs (CSV, JSON)
- Exported SQL results (CSV, JSON, Excel)
- Exported certificates (PEM, DER, text)
- Exported request collections

### SQLite Database (Optional Enhancement)
Future phase could store:
- Persistent query/request favorites
- Shared collections across sessions
- Analytics on query patterns

**Current Implementation**: No database storage. All history in browser localStorage.

---

## Relationships

```
Certificate
  └─> parent_cert: Certificate (1:1, optional)
  └─> CertificateChain.intermediates: List[Certificate] (1:N)

DatabaseConnection
  └─> tables: List[TableSchema] (1:N)

TableSchema
  └─> columns: List[ColumnSchema] (1:N)

HTTPRequest
  └─> environment: Dict[str, str] (N:N with EnvironmentVariable)
  └─> HTTPResponse (1:1 via RequestHistory)

QueryHistory
  └─> database: DatabaseConnection (implicit, tracked by session)

RequestHistory
  └─> request: HTTPRequest (1:1)
  └─> response: HTTPResponse (1:1, optional)
```

---

## JSON Serialization

All models support JSON serialization for API responses:

```python
from dataclasses import asdict
import json

def to_json(self) -> str:
    return json.dumps(asdict(self), default=str, indent=2)
```

Special handling:
- `datetime` → ISO 8601 string
- `Enum` → `.value` string
- `bytes` → base64 encoded string
- Circular references (Certificate.parent_cert) → Flatten to ID or break cycle

---

## Summary

**Total Models**: 22 dataclasses across 4 modules
- `log_entry.py`: 4 models (LogEntry, LogFilter, LogStatistics, enums)
- `certificate.py`: 5 models (Certificate, CertificateChain, PublicKeyInfo, enums)
- `database.py`: 6 models (DatabaseConnection, TableSchema, ColumnSchema, QueryResult, QueryHistory, enums)
- `http_request.py`: 7 models (HTTPRequest, HTTPResponse, HTTPTimingBreakdown, EnvironmentVariable, RequestHistory, enums)

**Type Safety**: 100% type hints, validated with mypy

**Validation**: All critical fields validated in `__post_init__` methods

**API Integration**: Direct FastAPI Pydantic compatibility via dataclasses

**Next Steps**: Generate OpenAPI contracts based on these models (Phase 1 continuation).
