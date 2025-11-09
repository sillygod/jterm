"""Security utilities for input validation and sanitization.

T059: Security hardening - input validation, SQL injection prevention, credential masking
"""

import re
from typing import Optional, Any
from pathlib import Path


class SecurityValidator:
    """Security validation and sanitization utilities."""

    # Dangerous SQL keywords that should raise warnings
    DANGEROUS_SQL_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'INSERT', 'UPDATE', 'EXEC', 'EXECUTE', 'GRANT',
        'REVOKE', 'SHUTDOWN', 'RESTORE'
    ]

    # Common SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"';.*--",  # SQL comment injection
        r"1=1",     # Always true condition
        r"OR\s+1=1",  # OR injection
        r"UNION\s+SELECT",  # UNION injection
        r"EXEC\s*\(",  # Stored procedure execution
        r"xp_.*cmdshell",  # Command execution
    ]

    @staticmethod
    def validate_file_path(file_path: str, allowed_extensions: Optional[list] = None) -> bool:
        """Validate file path for security issues.

        Args:
            file_path: Path to validate
            allowed_extensions: Optional list of allowed file extensions

        Returns:
            True if path is safe, False otherwise

        Raises:
            ValueError: If path contains dangerous patterns
        """
        if not file_path:
            raise ValueError("File path cannot be empty")

        # Check for path traversal attempts
        if '..' in file_path:
            raise ValueError("Path traversal detected: '..' not allowed in file paths")

        # Check for absolute path (should not start with /)
        # Allow absolute paths but validate them
        path = Path(file_path)

        # Check if path exists (optional, depends on use case)
        # For now, we just validate the format

        # Check file extension if provided
        if allowed_extensions:
            ext = path.suffix.lower()
            if ext not in allowed_extensions:
                raise ValueError(f"File extension '{ext}' not allowed. Allowed: {allowed_extensions}")

        return True

    @staticmethod
    def validate_sql_query(query: str, allow_writes: bool = False) -> bool:
        """Validate SQL query for security issues.

        Args:
            query: SQL query to validate
            allow_writes: Whether to allow write operations

        Returns:
            True if query is safe, False otherwise

        Raises:
            ValueError: If query contains dangerous patterns
        """
        if not query or not query.strip():
            raise ValueError("SQL query cannot be empty")

        # Normalize query for checking
        query_upper = query.upper()

        # Check for dangerous keywords if writes not allowed
        if not allow_writes:
            for keyword in SecurityValidator.DANGEROUS_SQL_KEYWORDS:
                if re.search(rf'\b{keyword}\b', query_upper):
                    raise ValueError(f"Dangerous SQL keyword detected: {keyword}. Read-only queries are enforced.")

        # Check for SQL injection patterns
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection pattern detected: {pattern}")

        # Check for excessive semicolons (multiple statements)
        semicolon_count = query.count(';')
        if semicolon_count > 1:
            raise ValueError("Multiple SQL statements not allowed (excessive semicolons detected)")

        return True

    @staticmethod
    def mask_credentials(text: str) -> str:
        """Mask credentials in text for logging.

        Args:
            text: Text that may contain credentials

        Returns:
            Text with credentials masked
        """
        # Mask password patterns
        patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\';\s]+)', r'password=***MASKED***'),
            (r'pwd["\']?\s*[:=]\s*["\']?([^"\';\s]+)', r'pwd=***MASKED***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\';\s]+)', r'secret=***MASKED***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\';\s]+)', r'token=***MASKED***'),
            (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\';\s]+)', r'api_key=***MASKED***'),
            (r'Bearer\s+([A-Za-z0-9\-._~+/]+=*)', r'Bearer ***MASKED***'),
            (r'Basic\s+([A-Za-z0-9+/]+=*)', r'Basic ***MASKED***'),
        ]

        masked = text
        for pattern, replacement in patterns:
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)

        return masked

    @staticmethod
    def validate_connection_string(conn_str: str) -> bool:
        """Validate database connection string.

        Args:
            conn_str: Connection string to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If connection string is invalid
        """
        if not conn_str or not conn_str.strip():
            raise ValueError("Connection string cannot be empty")

        # Check for common database protocols
        valid_protocols = ['sqlite://', 'postgresql://', 'mysql://', 'mariadb://']
        if not any(conn_str.startswith(proto) for proto in valid_protocols):
            raise ValueError(f"Invalid database protocol. Supported: {valid_protocols}")

        # SQLite specific validation
        if conn_str.startswith('sqlite://'):
            # Extract file path after sqlite:///
            if conn_str.startswith('sqlite:///'):
                file_path = conn_str[10:]  # Remove 'sqlite:///'
                SecurityValidator.validate_file_path(file_path, allowed_extensions=['.db', '.sqlite', '.sqlite3'])

        return True

    @staticmethod
    def sanitize_input(value: Any, max_length: Optional[int] = None) -> str:
        """Sanitize user input.

        Args:
            value: Input value to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            ValueError: If input is invalid
        """
        if value is None:
            return ""

        # Convert to string
        sanitized = str(value).strip()

        # Check length
        if max_length and len(sanitized) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length} characters")

        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')

        # Check for control characters (except common ones like newline, tab)
        if re.search(r'[\x01-\x08\x0B-\x0C\x0E-\x1F]', sanitized):
            raise ValueError("Invalid control characters detected in input")

        return sanitized

    @staticmethod
    def validate_regex_pattern(pattern: str) -> bool:
        """Validate regex pattern for security issues.

        Args:
            pattern: Regex pattern to validate

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If pattern is invalid or dangerous
        """
        if not pattern:
            return True  # Empty pattern is safe

        # Check for ReDoS (Regular Expression Denial of Service) patterns
        # This is a simplified check
        if len(pattern) > 1000:
            raise ValueError("Regex pattern too long (potential ReDoS attack)")

        # Check for excessive nesting
        nesting_level = pattern.count('(') - pattern.count('(?:')
        if nesting_level > 10:
            raise ValueError("Excessive regex nesting detected (potential ReDoS attack)")

        # Try to compile the pattern
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {str(e)}")

        return True
