"""HTTP request service for curlcat command."""

import time
import json
import base64
import asyncio
import tempfile
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
        self.use_curl_timing = True  # Use curl for accurate timing data

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

        # Use curl for accurate timing if enabled
        if self.use_curl_timing:
            return await self._execute_with_curl(request)

        # Fallback to httpx
        return await self._execute_with_httpx(request)

    async def _execute_with_curl(self, request: HTTPRequest) -> HTTPResponse:
        """
        Execute request using curl command for accurate timing data.

        Args:
            request: HTTPRequest object

        Returns:
            HTTPResponse with accurate timing breakdown
        """
        timing = HTTPTimingBreakdown()

        try:
            # Build curl command
            curl_cmd = ['curl', '-s', '-S']  # Silent but show errors

            # Add method
            curl_cmd.extend(['-X', request.method.value])

            # Add headers
            for key, value in request.headers.items():
                curl_cmd.extend(['-H', f'{key}: {value}'])

            # Add body if present
            if request.body:
                curl_cmd.extend(['-d', request.body])

            # Add authentication
            if request.auth_type == AuthType.BASIC and request.auth_credentials:
                if ':' in request.auth_credentials:
                    curl_cmd.extend(['-u', request.auth_credentials])
            elif request.auth_type == AuthType.BEARER and request.auth_credentials:
                curl_cmd.extend(['-H', f'Authorization: Bearer {request.auth_credentials}'])

            # SSL verification
            if not request.verify_ssl:
                curl_cmd.append('-k')

            # Follow redirects
            if request.follow_redirects:
                curl_cmd.append('-L')

            # Timeout
            curl_cmd.extend(['--max-time', str(request.timeout_seconds)])

            # Write response headers to temp file
            headers_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt')
            headers_file.close()
            curl_cmd.extend(['-D', headers_file.name])

            # Add timing output format
            timing_format = (
                'time_namelookup:%{time_namelookup}\\n'
                'time_connect:%{time_connect}\\n'
                'time_appconnect:%{time_appconnect}\\n'
                'time_pretransfer:%{time_pretransfer}\\n'
                'time_redirect:%{time_redirect}\\n'
                'time_starttransfer:%{time_starttransfer}\\n'
                'time_total:%{time_total}\\n'
                'http_code:%{http_code}\\n'
            )
            curl_cmd.extend(['-w', timing_format])

            # Add URL
            curl_cmd.append(request.url)

            # Execute curl
            process = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            # Parse output
            output = stdout.decode('utf-8')
            lines = output.split('\n')

            # Extract timing data and response body
            timing_data = {}
            body_lines = []
            status_code = 200

            for line in lines:
                if ':' in line and line.startswith('time_'):
                    key, value = line.split(':', 1)
                    try:
                        timing_data[key] = float(value) * 1000  # Convert to ms
                    except ValueError:
                        pass
                elif line.startswith('http_code:'):
                    try:
                        status_code = int(line.split(':', 1)[1])
                    except ValueError:
                        pass
                else:
                    body_lines.append(line)

            response_body = '\n'.join(body_lines).strip()

            # Parse response headers
            response_headers = {}
            try:
                with open(headers_file.name, 'r') as f:
                    header_lines = f.read().split('\n')
                    for line in header_lines[1:]:  # Skip status line
                        if ':' in line:
                            key, value = line.split(':', 1)
                            response_headers[key.strip()] = value.strip()
            except Exception:
                pass
            finally:
                import os
                try:
                    os.unlink(headers_file.name)
                except Exception:
                    pass

            # Build timing breakdown
            timing.dns_lookup_ms = timing_data.get('time_namelookup', 0)
            timing.tcp_connect_ms = timing_data.get('time_connect', 0) - timing.dns_lookup_ms
            timing.tls_handshake_ms = timing_data.get('time_appconnect', 0) - timing_data.get('time_connect', 0)
            timing.server_processing_ms = timing_data.get('time_starttransfer', 0) - timing_data.get('time_pretransfer', 0)
            timing.transfer_ms = timing_data.get('time_total', 0) - timing_data.get('time_starttransfer', 0)
            timing.total_ms = timing_data.get('time_total', 0)

            # Build response
            http_response = HTTPResponse(
                status_code=status_code,
                headers=response_headers,
                body=response_body,
                timing=timing,
                redirect_chain=[]
            )

            return http_response

        except Exception as e:
            raise Exception(f"Curl execution failed: {str(e)}") from e

    async def _execute_with_httpx(self, request: HTTPRequest) -> HTTPResponse:
        """
        Fallback method using httpx (with estimated timing).

        Args:
            request: HTTPRequest object

        Returns:
            HTTPResponse with estimated timing
        """
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

            # Estimate timing phases based on typical network behavior
            # httpx doesn't expose socket-level timing, so we estimate based on:
            # - URL scheme (http vs https)
            # - Total request time
            # - Typical network latency patterns

            is_https = request.url.startswith('https://')

            if timing.total_ms > 0:
                # Rough estimates based on typical network behavior:
                # DNS: ~10-50ms (8% of total)
                # TCP: ~20-100ms (12% of total)
                # TLS: ~50-200ms for HTTPS (25% of total)
                # Server: remainder

                # DNS lookup (estimate 8% of total time, min 10ms, max 100ms)
                timing.dns_lookup_ms = max(10, min(100, timing.total_ms * 0.08))

                # TCP connect (estimate 12% of total time, min 15ms, max 150ms)
                timing.tcp_connect_ms = max(15, min(150, timing.total_ms * 0.12))

                # TLS handshake for HTTPS (estimate 25% of total time, min 30ms, max 300ms)
                if is_https:
                    timing.tls_handshake_ms = max(30, min(300, timing.total_ms * 0.25))
                else:
                    timing.tls_handshake_ms = 0

                # Server processing time (remainder)
                connection_time = timing.dns_lookup_ms + timing.tcp_connect_ms + timing.tls_handshake_ms
                timing.server_processing_ms = max(0, timing.total_ms - connection_time - 10)

                # Transfer time (estimate 5% of total, min 5ms)
                timing.transfer_ms = max(5, timing.total_ms * 0.05)

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
