"""HTTP request and response models for curlcat command."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import re


class HTTPMethod(Enum):
    """Supported HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(Enum):
    """Authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"


@dataclass
class HTTPRequest:
    """HTTP request representation."""
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
        """Validate request parameters."""
        # Validate URL
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {self.url}")

        # Validate timeout
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ValueError(f"Timeout must be 1-300 seconds, got {self.timeout_seconds}")

        # Ensure method is HTTPMethod enum
        if isinstance(self.method, str):
            self.method = HTTPMethod(self.method.upper())

        # Ensure auth_type is AuthType enum
        if isinstance(self.auth_type, str):
            self.auth_type = AuthType(self.auth_type.lower())

    def substitute_variables(self) -> 'HTTPRequest':
        """Replace {{VAR}} placeholders with environment values."""
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
        """Generate equivalent curl command."""
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


@dataclass
class HTTPTimingBreakdown:
    """Detailed timing information."""
    dns_lookup_ms: float = 0  # DNS resolution time
    tcp_connect_ms: float = 0  # TCP connection establishment
    tls_handshake_ms: float = 0  # TLS handshake (if HTTPS)
    server_processing_ms: float = 0  # Time to first byte
    transfer_ms: float = 0  # Data transfer time
    total_ms: float = 0  # Total request time

    @property
    def formatted_total(self) -> str:
        """Human-readable total time."""
        if self.total_ms < 1000:
            return f"{int(self.total_ms)}ms"
        else:
            return f"{self.total_ms / 1000:.2f}s"


@dataclass
class HTTPResponse:
    """HTTP response representation."""
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    timing: HTTPTimingBreakdown = field(default_factory=HTTPTimingBreakdown)

    # Redirect chain (if followed)
    redirect_chain: List[str] = field(default_factory=list)

    # Certificate info (if HTTPS)
    certificate: Optional['Certificate'] = None  # Forward reference, imported at runtime if needed

    @property
    def content_type(self) -> Optional[str]:
        """Extract Content-Type header."""
        return self.headers.get('content-type') or self.headers.get('Content-Type')

    @property
    def is_json(self) -> bool:
        """Check if response is JSON."""
        ct = self.content_type
        return ct is not None and 'application/json' in ct

    @property
    def is_html(self) -> bool:
        """Check if response is HTML."""
        ct = self.content_type
        return ct is not None and 'text/html' in ct

    @property
    def status_category(self) -> str:
        """HTTP status category."""
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
    """Reusable environment variable for curlcat."""
    name: str
    value: str
    description: Optional[str] = None  # User annotation

    def __post_init__(self):
        """Validate variable name."""
        # Validate name (alphanumeric + underscore only)
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', self.name):
            raise ValueError(f"Invalid variable name: {self.name}. Use UPPERCASE_WITH_UNDERSCORES")


@dataclass
class RequestHistory:
    """Saved HTTP request with response."""
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
        """Human-readable name."""
        if self.name:
            return self.name
        return f"{self.request.method.value} {self.request.url}"
