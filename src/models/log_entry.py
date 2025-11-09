"""Log entry data models for logcat functionality.

This module provides data classes for log parsing, filtering, and statistics.
Implements T011, T012, T013.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import re


class LogLevel(Enum):
    """Log severity levels."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogFormat(Enum):
    """Supported log file formats."""
    JSON = "json"
    APACHE_COMBINED = "apache_combined"
    APACHE_COMMON = "apache_common"
    NGINX_ERROR = "nginx_error"
    PLAIN_TEXT = "plain_text"


@dataclass
class LogEntry:
    """Represents a single log line.

    T011: LogEntry model with comprehensive field support.
    """
    timestamp: datetime
    level: LogLevel
    message: str
    source: Optional[str] = None  # Log source (file, module, service)
    line_number: int = 0  # Line number in original file
    raw_text: str = ""  # Original unparsed line

    # Structured fields (JSON logs only)
    structured_fields: Dict[str, Any] = field(default_factory=dict)

    # Stack trace (if present)
    stack_trace: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"Invalid timestamp: {self.timestamp}")

        # Normalize level to uppercase and convert to enum
        if isinstance(self.level, str):
            try:
                self.level = LogLevel(self.level.upper())
            except ValueError:
                # Default to INFO if level is unknown
                self.level = LogLevel.INFO

        # Ensure line_number is non-negative
        if self.line_number < 0:
            self.line_number = 0

    @property
    def is_error(self) -> bool:
        """Check if log is error or fatal level."""
        return self.level in [LogLevel.ERROR, LogLevel.FATAL]

    @property
    def display_time(self) -> str:
        """Human-readable timestamp with milliseconds."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "line_number": self.line_number,
            "raw_text": self.raw_text,
            "structured_fields": self.structured_fields,
            "stack_trace": self.stack_trace,
            "is_error": self.is_error,
            "display_time": self.display_time
        }


@dataclass
class LogFilter:
    """Filter criteria for log entries.

    T012: LogFilter model with multiple filter options.
    """
    levels: List[LogLevel] = field(default_factory=list)  # Empty = all levels
    search_pattern: Optional[str] = None  # Regex pattern
    since: Optional[datetime] = None  # Start time filter
    until: Optional[datetime] = None  # End time filter
    source: Optional[str] = None  # Source filter (file, module)
    has_stack_trace: Optional[bool] = None  # Only logs with stack traces

    def __post_init__(self):
        """Validate filter parameters."""
        # Validate time range
        if self.since and self.until and self.since > self.until:
            raise ValueError("'since' time must be before 'until' time")

        # Validate regex pattern
        if self.search_pattern:
            try:
                re.compile(self.search_pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry matches filter criteria.

        Args:
            entry: LogEntry to test against filter

        Returns:
            True if entry matches all filter criteria
        """
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

        # Search pattern (regex) - search in message and raw_text
        if self.search_pattern:
            pattern = re.compile(self.search_pattern)
            if not (pattern.search(entry.message) or pattern.search(entry.raw_text)):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "levels": [level.value for level in self.levels],
            "search_pattern": self.search_pattern,
            "since": self.since.isoformat() if self.since else None,
            "until": self.until.isoformat() if self.until else None,
            "source": self.source,
            "has_stack_trace": self.has_stack_trace
        }


@dataclass
class LogStatistics:
    """Aggregate statistics for log analysis.

    T013: LogStatistics model with comprehensive metrics.
    """
    total_entries: int = 0
    level_counts: Dict[LogLevel, int] = field(default_factory=dict)
    time_range: tuple = field(default=(None, None))
    sources: List[str] = field(default_factory=list)
    error_rate: float = 0.0  # Percentage of ERROR/FATAL logs

    @classmethod
    def from_entries(cls, entries: List[LogEntry]) -> 'LogStatistics':
        """Calculate statistics from log entries.

        Args:
            entries: List of LogEntry objects to analyze

        Returns:
            LogStatistics object with computed metrics
        """
        if not entries:
            return cls()

        # Count entries by level
        level_counts = {}
        for entry in entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1

        # Calculate error rate
        error_count = sum(1 for e in entries if e.is_error)
        error_rate = (error_count / len(entries)) * 100 if entries else 0

        # Extract unique sources
        sources = list(set(e.source for e in entries if e.source))

        # Determine time range
        timestamps = [e.timestamp for e in entries]
        time_range = (min(timestamps), max(timestamps)) if timestamps else (None, None)

        return cls(
            total_entries=len(entries),
            level_counts=level_counts,
            time_range=time_range,
            sources=sorted(sources),
            error_rate=round(error_rate, 2)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_entries": self.total_entries,
            "level_counts": {level.value: count for level, count in self.level_counts.items()},
            "time_range": {
                "start": self.time_range[0].isoformat() if self.time_range[0] else None,
                "end": self.time_range[1].isoformat() if self.time_range[1] else None
            },
            "sources": self.sources,
            "error_rate": self.error_rate
        }

    @property
    def summary(self) -> str:
        """Human-readable summary of statistics."""
        if self.total_entries == 0:
            return "No log entries"

        parts = [f"{self.total_entries} total entries"]

        # Add error rate if significant
        if self.error_rate > 0:
            parts.append(f"{self.error_rate}% errors")

        # Add time range if available
        if self.time_range[0] and self.time_range[1]:
            duration = self.time_range[1] - self.time_range[0]
            parts.append(f"spanning {duration}")

        return ", ".join(parts)
