"""HTTP request service for curlcat command."""

import time
import json
import base64
from typing import Dict, Optional
import httpx

from src.models.http_request import (
    HTTPRequest,
    HTTPResponse,
    HTTPTimingBreakdown,
    HTTPMethod,
    AuthType,
    EnvironmentVariable
)


class HTTPService:
    """Service for executing HTTP requests and managing request history."""

    def __init__(self):
        """Initialize HTTP service."""
        self.environment_variables: Dict[str, EnvironmentVariable] = {}

    async def execute_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Execute an HTTP request with detailed timing.

        Args:
            request: HTTPRequest object with all request details

        Returns:
            HTTPResponse object with response data and timing

        Raises:
            httpx.HTTPError: If request fails
        """
        # Substitute environment variables
        if request.environment:
            request = request.substitute_variables()

        # Prepare timing breakdown
        timing = HTTPTimingBreakdown()
        start_time = time.perf_counter()

        try:
            # Build request kwargs
            request_kwargs = {
                'method': request.method.value,
                'url': request.url,
                'headers': request.headers,
                'timeout': request.timeout_seconds,
                'follow_redirects': request.follow_redirects,
            }

            # Add body if present
            if request.body:
                # Determine content type for body
                content_type = request.headers.get('Content-Type', request.headers.get('content-type'))
                if content_type and 'application/json' in content_type:
                    # Parse JSON body
                    try:
                        request_kwargs['json'] = json.loads(request.body)
                    except json.JSONDecodeError:
                        request_kwargs['content'] = request.body
                else:
                    request_kwargs['content'] = request.body

            # Configure SSL verification
            if not request.verify_ssl:
                request_kwargs['verify'] = False

            # Add authentication
            if request.auth_type == AuthType.BASIC and request.auth_credentials:
                # Parse "user:pass" format
                if ':' in request.auth_credentials:
                    username, password = request.auth_credentials.split(':', 1)
                    request_kwargs['auth'] = (username, password)
                else:
                    # Try to decode base64
                    try:
                        decoded = base64.b64decode(request.auth_credentials).decode('utf-8')
                        if ':' in decoded:
                            username, password = decoded.split(':', 1)
                            request_kwargs['auth'] = (username, password)
                    except Exception:
                        pass
            elif request.auth_type == AuthType.BEARER and request.auth_credentials:
                # Add Authorization header
                if 'Authorization' not in request_kwargs['headers']:
                    request_kwargs['headers']['Authorization'] = f"Bearer {request.auth_credentials}"

            # Execute request
            redirect_chain = []

            async with httpx.AsyncClient() as client:
                # Track redirect chain manually if follow_redirects is True
                response = await client.request(**request_kwargs)

                # Collect redirect history
                if hasattr(response, 'history'):
                    redirect_chain = [str(r.url) for r in response.history]

            # Calculate total time
            end_time = time.perf_counter()
            timing.total_ms = (end_time - start_time) * 1000

            # Note: httpx doesn't expose detailed timing phases (DNS, TCP, TLS)
            # We provide total time and estimate transfer time
            # For more detailed breakdown, would need to use aiohttp with custom traces
            # or parse curl --write-out output

            # Extract response data
            response_headers = dict(response.headers)
            response_body = response.text

            # Build HTTPResponse
            http_response = HTTPResponse(
                status_code=response.status_code,
                headers=response_headers,
                body=response_body,
                timing=timing,
                redirect_chain=redirect_chain
            )

            return http_response

        except httpx.TimeoutException as e:
            # Timeout error
            timing.total_ms = (time.perf_counter() - start_time) * 1000
            raise Exception(f"Request timeout after {request.timeout_seconds}s") from e
        except httpx.ConnectError as e:
            # Connection error
            timing.total_ms = (time.perf_counter() - start_time) * 1000
            raise Exception(f"Connection failed: {str(e)}") from e
        except httpx.HTTPError as e:
            # Other HTTP errors
            timing.total_ms = (time.perf_counter() - start_time) * 1000
            raise Exception(f"HTTP error: {str(e)}") from e
        except Exception as e:
            # Catch-all for other errors
            timing.total_ms = (time.perf_counter() - start_time) * 1000
            raise Exception(f"Request failed: {str(e)}") from e

    def substitute_variables(self, text: str, environment: Dict[str, str]) -> str:
        """
        Substitute {{VAR}} placeholders in text with environment values.

        Args:
            text: Text containing {{VAR}} placeholders
            environment: Dictionary of variable name -> value

        Returns:
            Text with variables substituted
        """
        import re
        result = text
        for var_name, var_value in environment.items():
            pattern = r'\{\{' + re.escape(var_name) + r'\}\}'
            result = re.sub(pattern, var_value, result)
        return result

    def export_as_code(self, request: HTTPRequest, language: str = "curl") -> str:
        """
        Export request as code in various languages.

        Args:
            request: HTTPRequest to export
            language: Target language (curl, python, javascript, etc.)

        Returns:
            Code snippet as string

        Raises:
            ValueError: If language is not supported
        """
        if language == "curl":
            return request.to_curl_command()

        elif language == "python":
            return self._export_as_python(request)

        elif language == "javascript":
            return self._export_as_javascript(request)

        else:
            raise ValueError(f"Unsupported export language: {language}")

    def _export_as_python(self, request: HTTPRequest) -> str:
        """Export request as Python requests code."""
        lines = ["import requests", ""]

        # URL
        lines.append(f"url = '{request.url}'")

        # Headers
        if request.headers:
            lines.append("headers = {")
            for key, value in request.headers.items():
                lines.append(f"    '{key}': '{value}',")
            lines.append("}")

        # Body
        if request.body:
            lines.append(f"data = '''{request.body}'''")

        # Build request call
        args = ["url"]
        if request.headers:
            args.append("headers=headers")
        if request.body:
            args.append("data=data")
        if not request.verify_ssl:
            args.append("verify=False")
        if request.timeout_seconds != 30:
            args.append(f"timeout={request.timeout_seconds}")

        lines.append("")
        lines.append(f"response = requests.{request.method.value.lower()}({', '.join(args)})")
        lines.append("print(response.status_code)")
        lines.append("print(response.text)")

        return "\n".join(lines)

    def _export_as_javascript(self, request: HTTPRequest) -> str:
        """Export request as JavaScript fetch code."""
        lines = []

        # URL
        lines.append(f"const url = '{request.url}';")

        # Options
        options = []
        options.append(f"  method: '{request.method.value}'")

        if request.headers:
            options.append("  headers: {")
            for key, value in request.headers.items():
                options.append(f"    '{key}': '{value}',")
            options.append("  }")

        if request.body:
            body_escaped = request.body.replace("'", "\\'").replace("\n", "\\n")
            options.append(f"  body: '{body_escaped}'")

        lines.append("")
        lines.append("const options = {")
        lines.extend(options)
        lines.append("};")

        lines.append("")
        lines.append("fetch(url, options)")
        lines.append("  .then(response => response.text())")
        lines.append("  .then(data => console.log(data))")
        lines.append("  .catch(error => console.error('Error:', error));")

        return "\n".join(lines)

    def add_environment_variable(self, var: EnvironmentVariable) -> None:
        """
        Add or update an environment variable.

        Args:
            var: EnvironmentVariable to add
        """
        self.environment_variables[var.name] = var

    def get_environment_variable(self, name: str) -> Optional[EnvironmentVariable]:
        """
        Get an environment variable by name.

        Args:
            name: Variable name

        Returns:
            EnvironmentVariable if found, None otherwise
        """
        return self.environment_variables.get(name)

    def get_all_environment_variables(self) -> Dict[str, EnvironmentVariable]:
        """
        Get all environment variables.

        Returns:
            Dictionary of variable name -> EnvironmentVariable
        """
        return dict(self.environment_variables)

    def remove_environment_variable(self, name: str) -> bool:
        """
        Remove an environment variable.

        Args:
            name: Variable name to remove

        Returns:
            True if variable was removed, False if not found
        """
        if name in self.environment_variables:
            del self.environment_variables[name]
            return True
        return False
