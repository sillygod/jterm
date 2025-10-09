"""Session recording service for terminal playback and export capabilities.

This service provides session recording with minimal performance impact (<5%),
compression, checkpoints for seeking, and multiple export formats.
"""

import asyncio
import gzip
import json
import logging
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import zlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from src.models.recording import Recording, RecordingStatus
from src.models.terminal_session import TerminalSession
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Terminal event type enumeration."""
    INPUT = "input"
    OUTPUT = "output"
    RESIZE = "resize"
    COMMAND = "command"
    STATUS = "status"
    METADATA = "metadata"


class ExportFormat(str, Enum):
    """Export format enumeration."""
    JSON = "json"
    ASCIINEMA = "asciinema"
    HTML = "html"
    TEXT = "text"


@dataclass
class RecordingConfig:
    """Recording configuration parameters."""
    max_events: int = 10000
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    checkpoint_interval: int = 50  # Events between checkpoints
    compression_level: int = 6
    enable_compression: bool = True
    buffer_size: int = 5000  # Increased to handle high-volume output
    flush_interval: float = 3.0  # Seconds - flush more frequently
    performance_monitoring: bool = True
    retention_days: int = 30


@dataclass
class RecordingEvent:
    """Individual recording event."""
    timestamp: str
    delta_time: int  # Milliseconds since last event
    event_type: EventType
    data: Any
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "timestamp": self.timestamp,
            "deltaTime": self.delta_time,
            "type": self.event_type.value,
            "data": self.data,
            "size": self.size,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecordingEvent":
        """Create event from dictionary."""
        return cls(
            timestamp=data["timestamp"],
            delta_time=data["deltaTime"],
            event_type=EventType(data["type"]),
            data=data["data"],
            size=data["size"],
            metadata=data.get("metadata", {})
        )


@dataclass
class RecordingCheckpoint:
    """Recording checkpoint for seeking."""
    timestamp: str
    event_index: int
    terminal_state: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "timestamp": self.timestamp,
            "eventIndex": self.event_index,
            "terminalState": self.terminal_state,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class RecordingStats:
    """Recording performance statistics."""
    start_time: float
    events_recorded: int = 0
    bytes_recorded: int = 0
    compression_ratio: float = 0.0
    processing_time: float = 0.0
    errors: int = 0
    last_flush: float = 0.0

    @property
    def recording_duration(self) -> float:
        """Calculate recording duration in seconds."""
        return time.time() - self.start_time

    @property
    def events_per_second(self) -> float:
        """Calculate events per second."""
        duration = self.recording_duration
        return self.events_recorded / duration if duration > 0 else 0

    @property
    def bytes_per_second(self) -> float:
        """Calculate bytes per second."""
        duration = self.recording_duration
        return self.bytes_recorded / duration if duration > 0 else 0


class RecordingError(Exception):
    """Base exception for recording operations."""
    pass


class RecordingBufferOverflowError(RecordingError):
    """Raised when recording buffer overflows."""
    pass


class RecordingNotFoundError(RecordingError):
    """Raised when recording is not found."""
    pass


class SessionRecorder:
    """Individual session recorder instance."""

    def __init__(self, session_id: str, config: RecordingConfig):
        self.session_id = session_id
        self.config = config
        self.recording_id: Optional[str] = None
        self.start_time = time.time()
        self.last_event_time = self.start_time
        self.stats = RecordingStats(start_time=self.start_time)

        # Event buffer for performance
        self._event_buffer: deque = deque(maxlen=config.buffer_size * 2)  # Thread-safe
        self._checkpoint_buffer: deque = deque(maxlen=1000)  # Thread-safe
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

        # Performance monitoring
        self._performance_start = time.time()
        self._performance_baseline = 0.0

        # Output batching (like asciinema) - batch outputs within 250ms window
        # This catches animation frames that can update every 70-160ms
        # Using a longer window to catch multiple animation frames in sequence
        self._output_batch: List[str] = []
        self._output_batch_start_time: Optional[float] = None
        self._output_batch_last_output_time: Optional[float] = None
        self._output_batch_task: Optional[asyncio.Task] = None
        self._output_batch_window_ms = 250  # Batch window in milliseconds
        self._output_batch_max_gap_ms = 180  # Max gap between consecutive outputs

    async def start_recording(self) -> str:
        """Start recording session."""
        try:
            logger.info(f"Starting recording for session {self.session_id}")

            # Create database recording
            recording = await self._create_recording()
            self.recording_id = recording.recording_id

            self._running = True

            # Start periodic flush task
            self._flush_task = asyncio.create_task(self._periodic_flush())

            # Baseline performance measurement
            if self.config.performance_monitoring:
                await self._measure_baseline_performance()

            # Record initial event
            await self.record_event(
                EventType.METADATA,
                {
                    "action": "recording_started",
                    "config": {
                        "compression": self.config.enable_compression,
                        "checkpoints": True
                    }
                }
            )

            logger.info(f"Recording started: {self.recording_id}")
            return self.recording_id

        except Exception as e:
            logger.error(f"Failed to start recording for session {self.session_id}: {e}")
            raise RecordingError(f"Failed to start recording: {e}") from e

    async def stop_recording(self) -> None:
        """Stop recording session."""
        if not self._running:
            return

        try:
            logger.info(f"Stopping recording for session {self.session_id}")

            self._running = False

            # Flush any pending output batch
            if self._output_batch:
                await self._flush_output_batch()

            # Cancel batch flush task
            if self._output_batch_task:
                self._output_batch_task.cancel()
                try:
                    await self._output_batch_task
                except asyncio.CancelledError:
                    pass

            # Cancel periodic flush task
            if self._flush_task:
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass

            # Record final event
            await self.record_event(
                EventType.METADATA,
                {
                    "action": "recording_stopped",
                    "stats": {
                        "events": self.stats.events_recorded,
                        "duration": self.stats.recording_duration,
                        "size": self.stats.bytes_recorded
                    }
                }
            )

            # Final flush
            await self._flush_buffers()

            # Update database
            await self._finalize_recording()

            logger.info(f"Recording stopped: {self.recording_id}")

        except Exception as e:
            logger.error(f"Error stopping recording {self.recording_id}: {e}")
            raise RecordingError(f"Failed to stop recording: {e}") from e

    async def record_event(self, event_type: EventType, data: Any, metadata: Dict[str, Any] = None) -> None:
        """Record a new event."""
        if not self._running:
            return

        try:
            # Batch OUTPUT events (like asciinema) to combine rapid consecutive outputs
            if event_type == EventType.OUTPUT and isinstance(data, str):
                await self._add_to_output_batch(data)
                return

            # For non-OUTPUT events, flush any pending output batch first
            if self._output_batch:
                await self._flush_output_batch()

            current_time = time.time()
            timestamp = datetime.fromtimestamp(current_time, timezone.utc).isoformat()

            # Calculate delta time
            delta_time = int((current_time - self.last_event_time) * 1000)
            self.last_event_time = current_time

            # Estimate event size without expensive JSON serialization
            if isinstance(data, str):
                event_size = len(data.encode('utf-8'))
            else:
                event_size = len(str(data).encode('utf-8'))

            # Create event
            event = RecordingEvent(
                timestamp=timestamp,
                delta_time=delta_time,
                event_type=event_type,
                data=data,
                size=event_size,
                metadata=metadata or {}
            )

            # Update statistics
            self.stats.events_recorded += 1
            self.stats.bytes_recorded += event_size

            # Add to buffer without holding lock for long
            self._event_buffer.append(event)

            # Check buffer overflow - schedule async flush instead of blocking
            if len(self._event_buffer) > self.config.buffer_size:
                # Don't await - let it run in background to avoid blocking
                asyncio.create_task(self._flush_buffers())

                # Auto-checkpoint
                if (self.stats.events_recorded % self.config.checkpoint_interval == 0 and
                    event_type == EventType.OUTPUT):
                    await self._create_checkpoint(f"Auto checkpoint at event {self.stats.events_recorded}")

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Error recording event: {e}")

    async def _add_to_output_batch(self, data: str) -> None:
        """Add output to batch buffer with sliding window batching."""
        current_time = time.time()

        # Check if we should extend the existing batch or start a new one
        if self._output_batch and self._output_batch_last_output_time:
            gap_ms = (current_time - self._output_batch_last_output_time) * 1000

            # If gap is too large or batch has been open too long, flush and start new
            batch_duration_ms = (current_time - self._output_batch_start_time) * 1000
            if gap_ms > self._output_batch_max_gap_ms or batch_duration_ms > self._output_batch_window_ms:
                await self._flush_output_batch()

        # Start new batch if needed
        if not self._output_batch:
            self._output_batch_start_time = current_time

            # Schedule batch flush after window expires
            delay = self._output_batch_window_ms / 1000.0
            self._output_batch_task = asyncio.create_task(self._delayed_flush_output_batch(delay))

        # Add to batch and update last output time
        self._output_batch.append(data)
        self._output_batch_last_output_time = current_time

    async def _delayed_flush_output_batch(self, delay: float) -> None:
        """Flush output batch after delay."""
        try:
            await asyncio.sleep(delay)
            await self._flush_output_batch()
        except asyncio.CancelledError:
            pass

    async def _flush_output_batch(self) -> None:
        """Flush batched output as single event."""
        if not self._output_batch:
            return

        try:
            # Debug logging
            logger.info(f"BATCH FLUSH: Combining {len(self._output_batch)} outputs into single event")

            # Combine all outputs in the batch
            combined_output = ''.join(self._output_batch)

            # Use the start time of the batch
            batch_start_time = self._output_batch_start_time or time.time()
            timestamp = datetime.fromtimestamp(batch_start_time, timezone.utc).isoformat()

            # Calculate delta time from last event
            delta_time = int((batch_start_time - self.last_event_time) * 1000)
            self.last_event_time = batch_start_time

            event_size = len(combined_output.encode('utf-8'))

            # Create single event for the batch
            event = RecordingEvent(
                timestamp=timestamp,
                delta_time=delta_time,
                event_type=EventType.OUTPUT,
                data=combined_output,
                size=event_size,
                metadata={}
            )

            # Update statistics
            self.stats.events_recorded += 1
            self.stats.bytes_recorded += event_size

            # Add to buffer
            self._event_buffer.append(event)

            # Check buffer overflow
            if len(self._event_buffer) > self.config.buffer_size:
                asyncio.create_task(self._flush_buffers())

            # Clear batch
            self._output_batch.clear()
            self._output_batch_start_time = None
            self._output_batch_last_output_time = None

        except Exception as e:
            logger.error(f"Error flushing output batch: {e}")

    async def add_checkpoint(self, description: str, terminal_state: str = "") -> None:
        """Add a manual checkpoint."""
        if not self._running:
            return

        await self._create_checkpoint(description, terminal_state)

    async def resize_terminal(self, cols: int, rows: int) -> None:
        """Record terminal resize event."""
        await self.record_event(
            EventType.RESIZE,
            {"cols": cols, "rows": rows}
        )

    async def _create_recording(self) -> Recording:
        """Create database recording record."""
        async with AsyncSessionLocal() as db:
            # Get session info
            session_result = await db.execute(
                select(TerminalSession).where(TerminalSession.session_id == self.session_id)
            )
            session = session_result.scalar_one_or_none()

            if not session:
                raise RecordingError(f"Session not found: {self.session_id}")

            recording = Recording(
                session_id=self.session_id,
                user_id=session.user_id,
                terminal_size=session.terminal_size,
                status=RecordingStatus.RECORDING
            )

            db.add(recording)
            await db.commit()
            await db.refresh(recording)

            return recording

    async def _create_checkpoint(self, description: str, terminal_state: str = "") -> None:
        """Create a recording checkpoint."""
        try:
            checkpoint = RecordingCheckpoint(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_index=len(self._event_buffer) + self.stats.events_recorded,
                terminal_state=terminal_state,
                description=description
            )

            async with self._lock:
                self._checkpoint_buffer.append(checkpoint)

        except Exception as e:
            logger.error(f"Error creating checkpoint: {e}")

    async def _periodic_flush(self) -> None:
        """Periodically flush buffers to database."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                if self._event_buffer or self._checkpoint_buffer:
                    await self._flush_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")

    async def _flush_buffers(self) -> None:
        """Flush event and checkpoint buffers to database."""
        if not self.recording_id:
            return

        async with self._lock:
            if not self._event_buffer and not self._checkpoint_buffer:
                return

            try:
                async with AsyncSessionLocal() as db:
                    # Get current recording
                    result = await db.execute(
                        select(Recording).where(Recording.recording_id == self.recording_id)
                    )
                    recording = result.scalar_one_or_none()

                    if not recording:
                        logger.error(f"Recording not found: {self.recording_id}")
                        return

                    # Process events
                    if self._event_buffer:
                        print(f"DEBUG FLUSH: Flushing {len(self._event_buffer)} events to database")
                        current_events = list(recording.events or [])
                        new_events = [event.to_dict() for event in self._event_buffer]

                        # Apply compression if enabled
                        if self.config.enable_compression:
                            new_events = await self._compress_events(new_events)
                            print(f"DEBUG FLUSH: After compression: {len(new_events)} items")

                        current_events.extend(new_events)

                        # Check size limits
                        if len(current_events) > self.config.max_events:
                            # Keep most recent events
                            current_events = current_events[-self.config.max_events:]

                        recording.events = current_events
                        recording.event_count = len(current_events)
                        print(f"DEBUG FLUSH: Updated recording with {len(current_events)} total events")

                    # Process checkpoints
                    if self._checkpoint_buffer:
                        current_checkpoints = list(recording.checkpoints or [])
                        new_checkpoints = [cp.to_dict() for cp in self._checkpoint_buffer]
                        current_checkpoints.extend(new_checkpoints)
                        recording.checkpoints = current_checkpoints

                    # Update statistics
                    recording.file_size = self.stats.bytes_recorded

                    await db.commit()

                    # Clear buffers
                    self._event_buffer.clear()
                    self._checkpoint_buffer.clear()
                    self.stats.last_flush = time.time()

            except Exception as e:
                self.stats.errors += 1
                logger.error(f"Error flushing buffers: {e}")

    async def _compress_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress events data if beneficial."""
        try:
            # Convert to JSON
            json_data = json.dumps(events)
            original_size = len(json_data.encode('utf-8'))

            # Compress
            compressed_data = zlib.compress(
                json_data.encode('utf-8'),
                level=self.config.compression_level
            )
            compressed_size = len(compressed_data)

            # Update compression ratio
            if original_size > 0:
                self.stats.compression_ratio = (1 - compressed_size / original_size) * 100

            # Return compressed if beneficial
            if compressed_size < original_size * 0.9:  # At least 10% savings
                return [{
                    "compressed": True,
                    "data": compressed_data.hex(),
                    "original_size": original_size,
                    "compressed_size": compressed_size
                }]
            else:
                return events

        except Exception as e:
            logger.error(f"Error compressing events: {e}")
            return events

    async def _finalize_recording(self) -> None:
        """Finalize recording in database."""
        if not self.recording_id:
            return

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Recording).where(Recording.recording_id == self.recording_id)
                )
                recording = result.scalar_one_or_none()

                if recording:
                    recording.stop_recording()
                    recording.compression_ratio = int(self.stats.compression_ratio)
                    await db.commit()

        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")

    async def _measure_baseline_performance(self) -> None:
        """Measure baseline performance impact."""
        try:
            # Simple CPU measurement
            start_time = time.time()
            operations = 0

            # Do some work to measure baseline
            for _ in range(10000):
                operations += 1

            self._performance_baseline = time.time() - start_time
            logger.debug(f"Baseline performance measured: {self._performance_baseline:.4f}s")

        except Exception as e:
            logger.error(f"Error measuring baseline performance: {e}")

    def get_performance_impact(self) -> float:
        """Calculate performance impact percentage."""
        if self._performance_baseline == 0:
            return 0.0

        current_overhead = self.stats.processing_time
        return (current_overhead / self._performance_baseline) * 100


class RecordingService:
    """Main service for session recording management."""

    def __init__(self, config: RecordingConfig = None):
        self.config = config or RecordingConfig()
        self._recorders: Dict[str, SessionRecorder] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_monitoring(self) -> None:
        """Start background monitoring and cleanup."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_recordings())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def start_recording(self, session_id: str) -> str:
        """Start recording for a session."""
        async with self._lock:
            if session_id in self._recorders:
                raise RecordingError(f"Recording already active for session {session_id}")

            recorder = SessionRecorder(session_id, self.config)
            recording_id = await recorder.start_recording()

            self._recorders[session_id] = recorder
            logger.info(f"Started recording {recording_id} for session {session_id}. Active recorders: {list(self._recorders.keys())}")

            return recording_id

    async def stop_recording(self, session_id: str) -> None:
        """Stop recording for a session."""
        async with self._lock:
            recorder = self._recorders.get(session_id)
            if not recorder:
                return

            await recorder.stop_recording()
            del self._recorders[session_id]

    async def record_input(self, session_id: str, data: str) -> None:
        """Record terminal input."""
        recorder = self._recorders.get(session_id)
        if recorder:
            await recorder.record_event(EventType.INPUT, data)

    async def record_output(self, session_id: str, data: str) -> None:
        """Record terminal output."""
        recorder = self._recorders.get(session_id)
        if recorder:
            print(f"DEBUG RECORD: Recording output for session {session_id}, event count: {recorder.stats.events_recorded}")
            await recorder.record_event(EventType.OUTPUT, data)
        else:
            print(f"DEBUG RECORD: No active recorder for session {session_id}. Active sessions: {list(self._recorders.keys())}")

    async def record_command(self, session_id: str, command: str, exit_code: int = 0) -> None:
        """Record command execution."""
        recorder = self._recorders.get(session_id)
        if recorder:
            await recorder.record_event(
                EventType.COMMAND,
                {"command": command, "exit_code": exit_code}
            )

    async def resize_terminal(self, session_id: str, cols: int, rows: int) -> None:
        """Record terminal resize."""
        recorder = self._recorders.get(session_id)
        if recorder:
            await recorder.resize_terminal(cols, rows)

    async def add_checkpoint(self, session_id: str, description: str) -> None:
        """Add manual checkpoint."""
        recorder = self._recorders.get(session_id)
        if recorder:
            await recorder.add_checkpoint(description)

    async def get_recording(self, recording_id: str) -> Optional[Recording]:
        """Get recording by ID."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Recording).where(Recording.recording_id == recording_id)
            )
            return result.scalar_one_or_none()

    async def get_events(
        self,
        recording_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get events for a recording with optional filters."""
        recording = await self.get_recording(recording_id)
        if not recording:
            raise RecordingNotFoundError(f"Recording not found: {recording_id}")

        events = recording.events or []

        # Decompress events if they are compressed
        decompressed_events = []
        for e in events:
            if isinstance(e, dict) and e.get("compressed"):
                # Decompress the batch
                try:
                    compressed_data = bytes.fromhex(e.get("data", ""))
                    decompressed = zlib.decompress(compressed_data)
                    decompressed_batch = json.loads(decompressed.decode('utf-8'))
                    decompressed_events.extend(decompressed_batch)
                except Exception as decompress_error:
                    logger.error(f"Failed to decompress events: {decompress_error}")
            else:
                decompressed_events.append(e)

        # Apply filters
        filtered_events = []
        for event in decompressed_events:
            # Time filters
            if start_time:
                event_time = datetime.fromisoformat(event.get("timestamp", ""))
                if event_time < start_time:
                    continue
            if end_time:
                event_time = datetime.fromisoformat(event.get("timestamp", ""))
                if event_time > end_time:
                    continue

            # Event type filter
            if event_types and event.get("type") not in event_types:
                continue

            filtered_events.append(event)

        # Apply pagination
        total = len(filtered_events)
        paginated_events = filtered_events[offset:offset + limit]

        return {
            "events": paginated_events,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    async def export_recording(self, recording_id: str, format: ExportFormat) -> str:
        """Export recording in specified format."""
        recording = await self.get_recording(recording_id)
        if not recording:
            raise RecordingNotFoundError(f"Recording not found: {recording_id}")

        if format == ExportFormat.JSON:
            return await self._export_json(recording)
        elif format == ExportFormat.ASCIINEMA:
            return await self._export_asciinema(recording)
        elif format == ExportFormat.HTML:
            return await self._export_html(recording)
        elif format == ExportFormat.TEXT:
            return await self._export_text(recording)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def get_session_recordings(self, session_id: str) -> List[Recording]:
        """Get all recordings for a session."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Recording)
                .where(Recording.session_id == session_id)
                .order_by(Recording.start_time.desc())
            )
            return result.scalars().all()

    async def delete_recording(self, recording_id: str, user_id: str) -> bool:
        """Delete a recording."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Recording).where(
                    Recording.recording_id == recording_id,
                    Recording.user_id == user_id
                )
            )
            recording = result.scalar_one_or_none()

            if not recording:
                return False

            await db.delete(recording)
            await db.commit()

            return True

    async def get_recording_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get recording statistics for active session."""
        recorder = self._recorders.get(session_id)
        if not recorder:
            return None

        return {
            "session_id": session_id,
            "recording_id": recorder.recording_id,
            "duration": recorder.stats.recording_duration,
            "events": recorder.stats.events_recorded,
            "bytes": recorder.stats.bytes_recorded,
            "events_per_second": recorder.stats.events_per_second,
            "bytes_per_second": recorder.stats.bytes_per_second,
            "compression_ratio": recorder.stats.compression_ratio,
            "performance_impact": recorder.get_performance_impact(),
            "errors": recorder.stats.errors
        }

    async def _cleanup_expired_recordings(self) -> None:
        """Background task to clean up expired recordings."""
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    # Find expired recordings
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)

                    result = await db.execute(
                        select(Recording).where(Recording.end_time <= cutoff_date)
                    )
                    expired_recordings = result.scalars().all()

                    # Delete expired recordings
                    for recording in expired_recordings:
                        await db.delete(recording)

                    await db.commit()

                    if expired_recordings:
                        logger.info(f"Cleaned up {len(expired_recordings)} expired recordings")

                await asyncio.sleep(3600)  # Check every hour

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in recording cleanup: {e}")
                await asyncio.sleep(3600)

    async def _export_json(self, recording: Recording) -> str:
        """Export recording as JSON and return file path."""
        import tempfile
        import os

        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix='.json', prefix=f'recording_{recording.recording_id}_')

        try:
            # Close the file descriptor first
            os.close(fd)

            # Write JSON to file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(recording.to_dict(), f, indent=2)

            return temp_path
        except Exception as e:
            # Clean up on error
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def _export_asciinema(self, recording: Recording) -> str:
        """Export recording in asciinema format and return file path."""
        import tempfile
        import os

        # Get decompressed events
        events_data = await self.get_events(recording.recording_id, limit=100000)
        events = events_data.get("events", [])

        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix='.cast', prefix=f'recording_{recording.recording_id}_')

        try:
            os.close(fd)

            # Asciinema v2 format
            header = {
                "version": 2,
                "width": recording.terminal_size.get("cols", 80),
                "height": recording.terminal_size.get("rows", 24),
                "timestamp": int(recording.start_time.timestamp()) if recording.start_time else 0
            }

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(header) + '\n')

                for event in events:
                    if event.get("type") in ["input", "output"]:
                        line = json.dumps([
                            event.get("deltaTime", 0) / 1000.0,  # Convert to seconds
                            "i" if event.get("type") == "input" else "o",
                            event.get("data", "")
                        ])
                        f.write(line + '\n')

            return temp_path
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def _export_html(self, recording: Recording) -> str:
        """Export recording as HTML with xterm.js playback controls."""
        # Get decompressed events
        events_data = await self.get_events(recording.recording_id, limit=100000)
        events = events_data.get("events", [])
        events_json = json.dumps(events)

        html_template = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal Recording - {recording.recording_id}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #1e1e1e;
            color: #fff;
        }}
        h1 {{
            margin-bottom: 20px;
        }}
        .info {{
            margin-bottom: 20px;
            padding: 10px;
            background: #2d2d2d;
            border-radius: 4px;
        }}
        .controls {{
            margin: 20px 0;
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        button {{
            padding: 8px 16px;
            background: #0e639c;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        button:hover {{
            background: #1177bb;
        }}
        button:disabled {{
            background: #555;
            cursor: not-allowed;
        }}
        #terminal-container {{
            background: #000;
            border-radius: 4px;
            padding: 10px;
        }}
        .time-display {{
            font-family: monospace;
            font-size: 14px;
        }}
        .speed-control {{
            display: flex;
            gap: 5px;
        }}
        .speed-btn {{
            padding: 6px 12px;
            background: #333;
        }}
        .speed-btn.active {{
            background: #0e639c;
        }}
    </style>
</head>
<body>
    <h1>Terminal Recording</h1>
    <div class="info">
        <div>Recording ID: {recording.recording_id}</div>
        <div>Duration: {recording.duration}ms</div>
        <div>Events: {recording.event_count}</div>
    </div>

    <div class="controls">
        <button id="playBtn" onclick="play()">▶ Play</button>
        <button id="pauseBtn" onclick="pause()" disabled>⏸ Pause</button>
        <button id="stopBtn" onclick="stop()">⏹ Stop</button>
        <div class="time-display">
            <span id="currentTime">00:00</span> / <span id="totalTime">00:00</span>
        </div>
        <div class="speed-control">
            <button class="speed-btn active" onclick="setSpeed(1)">1x</button>
            <button class="speed-btn" onclick="setSpeed(1.5)">1.5x</button>
            <button class="speed-btn" onclick="setSpeed(2)">2x</button>
        </div>
    </div>

    <div id="terminal-container"></div>

    <script>
        const events = {events_json};
        let terminal;
        let currentIndex = 0;
        let isPlaying = false;
        let playbackSpeed = 1;
        let playbackTimer = null;
        let startTime = 0;

        // Initialize xterm
        terminal = new Terminal({{
            cursorBlink: false,
            rows: 24,
            cols: 80,
            theme: {{
                background: '#000000',
                foreground: '#ffffff'
            }}
        }});
        terminal.open(document.getElementById('terminal-container'));

        // Calculate total duration
        const totalDuration = {recording.duration};
        document.getElementById('totalTime').textContent = formatTime(totalDuration);

        function formatTime(ms) {{
            const seconds = Math.floor(ms / 1000);
            const minutes = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${{String(minutes).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}`;
        }}

        function play() {{
            if (!isPlaying) {{
                isPlaying = true;
                document.getElementById('playBtn').disabled = true;
                document.getElementById('pauseBtn').disabled = false;
                playNext();
            }}
        }}

        function pause() {{
            isPlaying = false;
            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            if (playbackTimer) {{
                clearTimeout(playbackTimer);
                playbackTimer = null;
            }}
        }}

        function stop() {{
            isPlaying = false;
            currentIndex = 0;
            startTime = 0;
            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            document.getElementById('currentTime').textContent = '00:00';
            terminal.clear();
            if (playbackTimer) {{
                clearTimeout(playbackTimer);
                playbackTimer = null;
            }}
        }}

        function setSpeed(speed) {{
            playbackSpeed = speed;
            document.querySelectorAll('.speed-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
        }}

        function playNext() {{
            if (!isPlaying || currentIndex >= events.length) {{
                if (currentIndex >= events.length) {{
                    stop();
                }}
                return;
            }}

            const event = events[currentIndex];

            // Update time display
            if (event.timestamp && events[0].timestamp) {{
                const eventTime = new Date(event.timestamp).getTime();
                const startEventTime = new Date(events[0].timestamp).getTime();
                const elapsed = eventTime - startEventTime;
                document.getElementById('currentTime').textContent = formatTime(elapsed);
            }}

            // Write output to terminal
            if (event.type === 'output') {{
                terminal.write(event.data);
            }}

            currentIndex++;

            // Schedule next event
            if (currentIndex < events.length) {{
                const nextEvent = events[currentIndex];
                const delay = (nextEvent.deltaTime || 0) / playbackSpeed;
                playbackTimer = setTimeout(playNext, delay);
            }} else {{
                stop();
            }}
        }}

        // Auto-play on load
        setTimeout(() => {{
            play();
        }}, 500);
    </script>
</body>
</html>
        '''

        # Write to temp file
        import tempfile
        import os

        fd, temp_path = tempfile.mkstemp(suffix='.html', prefix=f'recording_{recording.recording_id}_')

        try:
            os.close(fd)

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html_template)

            return temp_path
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def _export_text(self, recording: Recording) -> str:
        """Export recording as plain text and return file path."""
        import tempfile
        import os

        # Get decompressed events
        events_data = await self.get_events(recording.recording_id, limit=100000)
        events = events_data.get("events", [])

        fd, temp_path = tempfile.mkstemp(suffix='.txt', prefix=f'recording_{recording.recording_id}_')

        try:
            os.close(fd)

            lines = [
                f"Terminal Recording: {recording.recording_id}",
                f"Session: {recording.session_id}",
                f"Duration: {recording.duration}ms",
                f"Events: {len(events)}",
                "=" * 50,
                ""
            ]

            for event in events:
                timestamp = event.get("timestamp", "")
                event_type = event.get("type", "")
                data = event.get("data", "")

                lines.append(f"[{timestamp}] {event_type.upper()}: {data}")

            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return temp_path
        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    async def shutdown(self) -> None:
        """Shutdown recording service."""
        logger.info("Shutting down recording service")

        await self.stop_monitoring()

        # Stop all active recordings
        tasks = []
        for session_id in list(self._recorders.keys()):
            tasks.append(self.stop_recording(session_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Recording service shutdown complete")


# Global service instance
recording_service = RecordingService()


async def get_recording_service() -> RecordingService:
    """Dependency injection for recording service."""
    return recording_service