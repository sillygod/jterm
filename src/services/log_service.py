"""Log service for parsing, filtering, and streaming log files.

This module provides business logic for logcat functionality.
Implements T014.
"""

import json
import re
import aiofiles
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from pathlib import Path

from src.models.log_entry import LogEntry, LogFilter, LogStatistics, LogLevel, LogFormat


class LogService:
    """Service for log file operations.

    T014: LogService with parse_line(), detect_format(), filter_entries(), stream_file() methods.
    """

    def __init__(self):
        """Initialize log service."""
        self.chunk_size = 8192  # Read buffer size for streaming

    def detect_format(self, first_line: str) -> LogFormat:
        """Auto-detect log format from first line.

        Args:
            first_line: First line of log file

        Returns:
            Detected LogFormat enum value
        """
        line = first_line.strip()

        # Try JSON (most specific)
        if line.startswith('{'):
            try:
                json.loads(line)
                return LogFormat.JSON
            except (json.JSONDecodeError, ValueError):
                pass

        # Apache Combined Log Format (has user-agent)
        # Example: 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /path HTTP/1.0" 200 2326 "http://ref.com" "Mozilla/4.0"
        if re.match(r'^\S+ \S+ \S+ \[.+?\] ".+?" \d+ \d+ ".+?" ".+?"', line):
            return LogFormat.APACHE_COMBINED

        # Apache Common Log Format (no user-agent)
        # Example: 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /path HTTP/1.0" 200 2326
        if re.match(r'^\S+ \S+ \S+ \[.+?\] ".+?" \d+ \d+', line):
            return LogFormat.APACHE_COMMON

        # Nginx Error Log Format
        # Example: 2023/10/15 14:30:45 [error] 1234#1234: *1 message
        if re.match(r'^\d{4}/\d{2}/\d{2} .+? \[\w+\]', line):
            return LogFormat.NGINX_ERROR

        # Fallback to plain text
        return LogFormat.PLAIN_TEXT

    def parse_line(self, line: str, line_number: int, log_format: LogFormat) -> Optional[LogEntry]:
        """Parse a single log line according to format.

        Args:
            line: Raw log line text
            line_number: Line number in file
            log_format: Detected or specified log format

        Returns:
            LogEntry object or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None

        try:
            if log_format == LogFormat.JSON:
                return self._parse_json_line(line, line_number)
            elif log_format == LogFormat.APACHE_COMBINED:
                return self._parse_apache_combined(line, line_number)
            elif log_format == LogFormat.APACHE_COMMON:
                return self._parse_apache_common(line, line_number)
            elif log_format == LogFormat.NGINX_ERROR:
                return self._parse_nginx_error(line, line_number)
            else:
                return self._parse_plain_text(line, line_number)
        except Exception as e:
            # If parsing fails, treat as plain text
            return self._parse_plain_text(line, line_number)

    def _parse_json_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        """Parse JSON log line."""
        try:
            data = json.loads(line)

            # Extract timestamp (common field names)
            timestamp_str = data.get('timestamp') or data.get('time') or data.get('date') or data.get('@timestamp')
            if timestamp_str:
                timestamp = self._parse_timestamp(timestamp_str)
            else:
                timestamp = datetime.now()

            # Extract level (common field names)
            level_str = data.get('level') or data.get('severity') or data.get('loglevel') or 'INFO'
            try:
                level = LogLevel(level_str.upper())
            except ValueError:
                level = LogLevel.INFO

            # Extract message (common field names)
            message = data.get('message') or data.get('msg') or data.get('text') or str(data)

            # Extract source (common field names)
            source = data.get('source') or data.get('logger') or data.get('name') or data.get('module')

            # Stack trace
            stack_trace = data.get('stack_trace') or data.get('stacktrace') or data.get('exception')

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=source,
                line_number=line_number,
                raw_text=line,
                structured_fields=data,
                stack_trace=stack_trace
            )
        except (json.JSONDecodeError, ValueError) as e:
            return None

    def _parse_apache_combined(self, line: str, line_number: int) -> Optional[LogEntry]:
        """Parse Apache Combined Log Format.

        Format: IP - - [timestamp] "method path protocol" status size "referer" "user-agent"
        """
        pattern = r'^(\S+) \S+ \S+ \[(.+?)\] "([A-Z]+) (\S+) (\S+)" (\d+) (\d+) "(.+?)" "(.+?)"'
        match = re.match(pattern, line)
        if not match:
            return None

        ip, timestamp_str, method, path, protocol, status, size, referer, user_agent = match.groups()

        # Parse Apache timestamp: 10/Oct/2000:13:55:36 -0700
        timestamp = datetime.strptime(timestamp_str.split()[0], "%d/%b/%Y:%H:%M:%S")

        # Determine level based on status code
        status_code = int(status)
        if status_code >= 500:
            level = LogLevel.ERROR
        elif status_code >= 400:
            level = LogLevel.WARN
        else:
            level = LogLevel.INFO

        message = f"{method} {path} - {status_code}"

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=ip,
            line_number=line_number,
            raw_text=line,
            structured_fields={
                "ip": ip,
                "method": method,
                "path": path,
                "protocol": protocol,
                "status": status_code,
                "size": int(size),
                "referer": referer,
                "user_agent": user_agent
            }
        )

    def _parse_apache_common(self, line: str, line_number: int) -> Optional[LogEntry]:
        """Parse Apache Common Log Format.

        Format: IP - - [timestamp] "method path protocol" status size
        """
        pattern = r'^(\S+) \S+ \S+ \[(.+?)\] "([A-Z]+) (\S+) (\S+)" (\d+) (\d+)'
        match = re.match(pattern, line)
        if not match:
            return None

        ip, timestamp_str, method, path, protocol, status, size = match.groups()

        # Parse Apache timestamp
        timestamp = datetime.strptime(timestamp_str.split()[0], "%d/%b/%Y:%H:%M:%S")

        # Determine level based on status code
        status_code = int(status)
        if status_code >= 500:
            level = LogLevel.ERROR
        elif status_code >= 400:
            level = LogLevel.WARN
        else:
            level = LogLevel.INFO

        message = f"{method} {path} - {status_code}"

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=ip,
            line_number=line_number,
            raw_text=line,
            structured_fields={
                "ip": ip,
                "method": method,
                "path": path,
                "protocol": protocol,
                "status": status_code,
                "size": int(size)
            }
        )

    def _parse_nginx_error(self, line: str, line_number: int) -> Optional[LogEntry]:
        """Parse Nginx Error Log Format.

        Format: 2023/10/15 14:30:45 [error] 1234#1234: *1 message
        """
        pattern = r'^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (\d+)#(\d+): (.+)$'
        match = re.match(pattern, line)
        if not match:
            return None

        timestamp_str, level_str, pid, tid, message = match.groups()

        # Parse timestamp
        timestamp = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")

        # Map nginx levels to LogLevel
        level_map = {
            "debug": LogLevel.DEBUG,
            "info": LogLevel.INFO,
            "notice": LogLevel.INFO,
            "warn": LogLevel.WARN,
            "error": LogLevel.ERROR,
            "crit": LogLevel.FATAL,
            "alert": LogLevel.FATAL,
            "emerg": LogLevel.FATAL
        }
        level = level_map.get(level_str.lower(), LogLevel.INFO)

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message.strip(),
            source=f"nginx:{pid}",
            line_number=line_number,
            raw_text=line,
            structured_fields={
                "pid": int(pid),
                "tid": int(tid)
            }
        )

    def _parse_plain_text(self, line: str, line_number: int) -> LogEntry:
        """Parse unstructured plain text log line."""
        # Try to extract timestamp from beginning of line
        timestamp_patterns = [
            (r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', "%Y-%m-%d %H:%M:%S"),
            (r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', "%Y-%m-%dT%H:%M:%S"),
            (r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', "%Y-%m-%d %H:%M:%S"),
        ]

        timestamp = datetime.now()
        message = line

        for pattern, fmt in timestamp_patterns:
            match = re.match(pattern, line)
            if match:
                try:
                    timestamp = datetime.strptime(match.group(1), fmt)
                    message = line[len(match.group(0)):].strip()
                    break
                except ValueError:
                    pass

        # Try to detect level from keywords
        level = LogLevel.INFO
        level_keywords = {
            LogLevel.TRACE: ['TRACE', 'VERBOSE'],
            LogLevel.DEBUG: ['DEBUG'],
            LogLevel.INFO: ['INFO', 'INFORMATION'],
            LogLevel.WARN: ['WARN', 'WARNING'],
            LogLevel.ERROR: ['ERROR', 'ERR'],
            LogLevel.FATAL: ['FATAL', 'CRITICAL', 'CRIT', 'EMERGENCY']
        }

        line_upper = line.upper()
        for log_level, keywords in level_keywords.items():
            if any(keyword in line_upper for keyword in keywords):
                level = log_level
                break

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            line_number=line_number,
            raw_text=line
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from various formats."""
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO 8601 with milliseconds and Z
            "%Y-%m-%dT%H:%M:%SZ",      # ISO 8601 with Z
            "%Y-%m-%dT%H:%M:%S.%f",    # ISO 8601 with milliseconds
            "%Y-%m-%dT%H:%M:%S",        # ISO 8601
            "%Y-%m-%d %H:%M:%S.%f",     # Space separated with milliseconds
            "%Y-%m-%d %H:%M:%S",        # Space separated
            "%d/%b/%Y:%H:%M:%S",        # Apache format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # If all else fails, return current time
        return datetime.now()

    def filter_entries(self, entries: List[LogEntry], log_filter: LogFilter) -> List[LogEntry]:
        """Filter log entries based on criteria.

        Args:
            entries: List of LogEntry objects
            log_filter: LogFilter with filter criteria

        Returns:
            Filtered list of LogEntry objects
        """
        return [entry for entry in entries if log_filter.matches(entry)]

    async def stream_file(self, file_path: str, log_format: Optional[LogFormat] = None,
                         log_filter: Optional[LogFilter] = None) -> AsyncGenerator[LogEntry, None]:
        """Stream log file line-by-line with parsing and filtering.

        Args:
            file_path: Path to log file
            log_format: Optional log format (auto-detected if None)
            log_filter: Optional filter to apply

        Yields:
            LogEntry objects that match filter criteria
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        # Read first line to detect format if not specified
        if log_format is None:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = await f.readline()
                log_format = self.detect_format(first_line)

        # Stream and parse file
        line_number = 0
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            async for line in f:
                line_number += 1
                entry = self.parse_line(line, line_number, log_format)

                if entry is None:
                    continue

                # Apply filter if provided
                if log_filter and not log_filter.matches(entry):
                    continue

                yield entry


# Singleton instance
_log_service = None


def get_log_service() -> LogService:
    """Get singleton LogService instance."""
    global _log_service
    if _log_service is None:
        _log_service = LogService()
    return _log_service
