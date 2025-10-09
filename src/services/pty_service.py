"""PTY service for terminal process management.

This service provides real-time terminal process management using Python's ptyprocess
library with async/await patterns for performance and proper resource cleanup.
"""

import asyncio
import logging
import os
import signal
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum

import ptyprocess
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models.terminal_session import TerminalSession, SessionStatus
from src.database.base import AsyncSessionLocal


logger = logging.getLogger(__name__)


class PTYStatus(str, Enum):
    """PTY process status enumeration."""
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PTYConfig:
    """PTY configuration parameters."""
    shell: str = "/bin/bash"
    cols: int = 80
    rows: int = 24
    cwd: str = "/"
    env: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    encoding: str = "utf-8"


@dataclass
class PTYStats:
    """PTY performance statistics."""
    start_time: float
    bytes_read: int = 0
    bytes_written: int = 0
    read_operations: int = 0
    write_operations: int = 0
    errors: int = 0

    @property
    def uptime_seconds(self) -> float:
        """Calculate uptime in seconds."""
        return time.time() - self.start_time

    @property
    def avg_bytes_per_read(self) -> float:
        """Calculate average bytes per read operation."""
        return self.bytes_read / self.read_operations if self.read_operations > 0 else 0

    @property
    def avg_bytes_per_write(self) -> float:
        """Calculate average bytes per write operation."""
        return self.bytes_written / self.write_operations if self.write_operations > 0 else 0


class PTYError(Exception):
    """Base exception for PTY operations."""
    pass


class PTYTimeoutError(PTYError):
    """Raised when PTY operation times out."""
    pass


class PTYProcessTerminatedError(PTYError):
    """Raised when PTY process has terminated."""
    pass


class PTYInstance:
    """Individual PTY instance managing a single terminal process."""

    def __init__(self, session_id: str, config: PTYConfig):
        self.session_id = session_id
        self.config = config
        self.process: Optional[ptyprocess.PtyProcess] = None
        self.status = PTYStatus.STARTING
        self.stats = PTYStats(start_time=time.time())
        self._output_callbacks: List[Callable[[bytes], None]] = []
        self._running = False
        self._read_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the PTY process."""
        try:
            print(f"DEBUG PTY: Starting PTY for session {self.session_id}")
            logger.info(f"Starting PTY for session {self.session_id}")

            # Prepare environment
            env = os.environ.copy()
            if self.config.env:
                env.update(self.config.env)

            # Add jterm bin directory to PATH for media viewing commands
            jterm_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bin')
            if os.path.exists(jterm_bin):
                current_path = env.get('PATH', '')
                if jterm_bin not in current_path:
                    env['PATH'] = f"{jterm_bin}:{current_path}"
                    logger.info(f"Added jterm bin directory to PATH: {jterm_bin}")

            # Start the PTY process
            self.process = ptyprocess.PtyProcess.spawn(
                [self.config.shell],
                dimensions=(self.config.rows, self.config.cols),
                cwd=self.config.cwd,
                env=env
            )

            self.status = PTYStatus.RUNNING
            self._running = True

            # Start reading output
            self._read_task = asyncio.create_task(self._read_output())

            print(f"DEBUG PTY: PTY started for session {self.session_id}, PID: {self.process.pid}")
            logger.info(f"PTY started for session {self.session_id}, PID: {self.process.pid}, shell: {self.config.shell}, cwd: {self.config.cwd}")

        except Exception as e:
            self.status = PTYStatus.ERROR
            self.stats.errors += 1
            logger.error(f"Failed to start PTY for session {self.session_id}: {e}")
            raise PTYError(f"Failed to start PTY: {e}") from e

    async def stop(self, force: bool = False) -> None:
        """Stop the PTY process."""
        async with self._lock:
            if not self.process or self.status == PTYStatus.STOPPED:
                return

            logger.info(f"Stopping PTY for session {self.session_id}")

            self._running = False

            # Cancel the read task
            if self._read_task:
                self._read_task.cancel()
                try:
                    await self._read_task
                except asyncio.CancelledError:
                    pass

            try:
                if force or not self.process.isalive():
                    # Force kill
                    if self.process.isalive():
                        self.process.kill(signal.SIGKILL)
                else:
                    # Graceful termination
                    self.process.terminate()

                    # Wait for process to terminate
                    try:
                        await asyncio.wait_for(
                            self._wait_for_termination(),
                            timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"PTY process did not terminate gracefully, force killing")
                        if self.process.isalive():
                            self.process.kill(signal.SIGKILL)

                self.status = PTYStatus.STOPPED
                logger.info(f"PTY stopped for session {self.session_id}")

            except Exception as e:
                self.status = PTYStatus.ERROR
                self.stats.errors += 1
                logger.error(f"Error stopping PTY for session {self.session_id}: {e}")
                raise PTYError(f"Failed to stop PTY: {e}") from e

    async def write(self, data: str) -> None:
        """Write data to the PTY process."""
        if not self.process or not self._running:
            raise PTYProcessTerminatedError("PTY process is not running")

        try:
            encoded_data = data.encode(self.config.encoding)
            self.process.write(encoded_data)

            self.stats.bytes_written += len(encoded_data)
            self.stats.write_operations += 1

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Error writing to PTY {self.session_id}: {e}")
            raise PTYError(f"Failed to write to PTY: {e}") from e

    async def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY terminal."""
        if not self.process or not self._running:
            raise PTYProcessTerminatedError("PTY process is not running")

        try:
            self.process.setwinsize(rows, cols)
            self.config.cols = cols
            self.config.rows = rows

            logger.debug(f"Resized PTY {self.session_id} to {cols}x{rows}")

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Error resizing PTY {self.session_id}: {e}")
            raise PTYError(f"Failed to resize PTY: {e}") from e

    def add_output_callback(self, callback: Callable[[bytes], None]) -> None:
        """Add a callback for processing output."""
        self._output_callbacks.append(callback)
        logger.info(f"Added output callback for session {self.session_id}, total callbacks: {len(self._output_callbacks)}")

    def remove_output_callback(self, callback: Callable[[bytes], None]) -> None:
        """Remove an output callback."""
        if callback in self._output_callbacks:
            self._output_callbacks.remove(callback)

    async def _read_output(self) -> None:
        """Continuously read output from the PTY process."""
        buffer = b""
        print(f"DEBUG PTY: Starting output reading loop for session {self.session_id}")
        logger.info(f"Starting output reading loop for session {self.session_id}")

        while self._running and self.process and self.process.isalive():
            try:
                # Non-blocking read with timeout
                data = await asyncio.wait_for(
                    self._read_pty_output(),
                    timeout=0.1
                )

                if data:
                    print(f"DEBUG PTY: Read {len(data)} bytes from PTY {self.session_id}: {data[:50]}")
                    logger.debug(f"Read {len(data)} bytes from PTY {self.session_id}")
                    buffer += data
                    self.stats.bytes_read += len(data)
                    self.stats.read_operations += 1

                    # Send data immediately to callbacks for real-time display
                    print(f"DEBUG PTY: Calling {len(self._output_callbacks)} callbacks with {len(data)} bytes immediately")
                    for callback in self._output_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Error in output callback: {e}")

                    # Clear buffer since we sent everything
                    buffer = b""

                    # Old line-based processing (commented out)
                    # Process complete lines
                    if False and (b'\n' in buffer or b'\r' in buffer):
                        if b'\n' in buffer:
                            line, buffer = buffer.split(b'\n', 1)
                            line += b'\n'
                        else:
                            line, buffer = buffer.split(b'\r', 1)
                            line += b'\r'

                        # Call output callbacks
                        print(f"DEBUG PTY: Calling {len(self._output_callbacks)} callbacks with {len(line)} bytes: {line[:50]}")
                        logger.debug(f"Calling {len(self._output_callbacks)} callbacks with {len(line)} bytes")
                        for callback in self._output_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(line)
                                else:
                                    callback(line)
                            except Exception as e:
                                logger.error(f"Error in output callback: {e}")

                    # If buffer is getting too large, send partial data
                    if len(buffer) > 4096:
                        for callback in self._output_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(buffer)
                                else:
                                    callback(buffer)
                            except Exception as e:
                                logger.error(f"Error in output callback: {e}")
                        buffer = b""

            except asyncio.TimeoutError:
                # Timeout is expected for non-blocking reads
                continue
            except Exception as e:
                self.stats.errors += 1
                logger.error(f"Error reading PTY output for {self.session_id}: {e}")
                break

        # Send any remaining buffer data
        if buffer:
            for callback in self._output_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(buffer)
                    else:
                        callback(buffer)
                except Exception as e:
                    logger.error(f"Error in output callback: {e}")

        logger.debug(f"PTY output reading stopped for session {self.session_id}")

    async def _read_pty_output(self) -> bytes:
        """Read output from PTY process asynchronously."""
        if not self.process or not self.process.isalive():
            print(f"DEBUG PTY: Process not alive in _read_pty_output")
            return b""

        try:
            # Use asyncio thread pool for blocking I/O with timeout
            loop = asyncio.get_event_loop()

            # Try non-blocking read first
            def try_read():
                try:
                    import select
                    import os
                    # Check if data is available
                    if hasattr(select, 'select'):
                        rlist, _, _ = select.select([self.process.fd], [], [], 0)
                        if rlist:
                            data = os.read(self.process.fd, 1024)
                            print(f"DEBUG PTY: Read {len(data)} bytes via os.read")
                            return data
                    return b""
                except Exception as e:
                    print(f"DEBUG PTY: Error in try_read: {e}")
                    return b""

            data = await loop.run_in_executor(None, try_read)
            return data
        except Exception as e:
            print(f"DEBUG PTY: Exception in _read_pty_output: {e}")
            import traceback
            traceback.print_exc()
            return b""

    async def _wait_for_termination(self) -> None:
        """Wait for the PTY process to terminate."""
        while self.process and self.process.isalive():
            await asyncio.sleep(0.1)

    def is_alive(self) -> bool:
        """Check if the PTY process is alive."""
        return self.process is not None and self.process.isalive()

    def get_stats(self) -> Dict[str, Any]:
        """Get PTY performance statistics."""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "pid": self.process.pid if self.process else None,
            "uptime_seconds": self.stats.uptime_seconds,
            "bytes_read": self.stats.bytes_read,
            "bytes_written": self.stats.bytes_written,
            "read_operations": self.stats.read_operations,
            "write_operations": self.stats.write_operations,
            "errors": self.stats.errors,
            "avg_bytes_per_read": self.stats.avg_bytes_per_read,
            "avg_bytes_per_write": self.stats.avg_bytes_per_write,
            "is_alive": self.is_alive()
        }


class PTYService:
    """Service for managing multiple PTY instances."""

    def __init__(self):
        self._instances: Dict[str, PTYInstance] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitoring_enabled = True

    async def start_monitoring(self) -> None:
        """Start background monitoring of PTY instances."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._monitor_instances())

    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring_enabled = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def create_pty(self, session_id: str, config: PTYConfig) -> PTYInstance:
        """Create and start a new PTY instance."""
        async with self._lock:
            if session_id in self._instances:
                raise PTYError(f"PTY instance already exists for session {session_id}")

            instance = PTYInstance(session_id, config)
            await instance.start()

            self._instances[session_id] = instance

            # Update database session
            await self._update_session_pty_info(session_id, instance.process.pid)

            logger.info(f"Created PTY instance for session {session_id}")
            return instance

    async def get_pty(self, session_id: str) -> Optional[PTYInstance]:
        """Get an existing PTY instance."""
        return self._instances.get(session_id)

    async def destroy_pty(self, session_id: str, force: bool = False) -> None:
        """Destroy a PTY instance."""
        async with self._lock:
            instance = self._instances.get(session_id)
            if not instance:
                return

            await instance.stop(force=force)
            del self._instances[session_id]

            # Update database session
            await self._update_session_pty_info(session_id, None)

            logger.info(f"Destroyed PTY instance for session {session_id}")

    async def write_to_pty(self, session_id: str, data: str) -> None:
        """Write data to a PTY instance."""
        instance = self._instances.get(session_id)
        if not instance:
            raise PTYError(f"No PTY instance found for session {session_id}")

        await instance.write(data)

    async def resize_pty(self, session_id: str, cols: int, rows: int) -> None:
        """Resize a PTY instance."""
        instance = self._instances.get(session_id)
        if not instance:
            raise PTYError(f"No PTY instance found for session {session_id}")

        await instance.resize(cols, rows)

        # Update database session
        await self._update_session_terminal_size(session_id, cols, rows)

    async def add_output_callback(self, session_id: str, callback: Callable[[bytes], None]) -> None:
        """Add an output callback to a PTY instance."""
        instance = self._instances.get(session_id)
        if not instance:
            raise PTYError(f"No PTY instance found for session {session_id}")

        instance.add_output_callback(callback)

    async def remove_output_callback(self, session_id: str, callback: Callable[[bytes], None]) -> None:
        """Remove an output callback from a PTY instance."""
        instance = self._instances.get(session_id)
        if instance:
            instance.remove_output_callback(callback)

    async def get_all_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all PTY instances."""
        stats = []
        for instance in self._instances.values():
            stats.append(instance.get_stats())
        return stats

    async def get_pty_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific PTY instance."""
        instance = self._instances.get(session_id)
        return instance.get_stats() if instance else None

    async def cleanup_dead_instances(self) -> int:
        """Clean up dead PTY instances."""
        dead_sessions = []

        for session_id, instance in self._instances.items():
            if not instance.is_alive():
                dead_sessions.append(session_id)

        for session_id in dead_sessions:
            await self.destroy_pty(session_id, force=True)

        if dead_sessions:
            logger.info(f"Cleaned up {len(dead_sessions)} dead PTY instances")

        return len(dead_sessions)

    async def _monitor_instances(self) -> None:
        """Background task to monitor PTY instances."""
        while self._monitoring_enabled:
            try:
                await self.cleanup_dead_instances()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in PTY monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _update_session_pty_info(self, session_id: str, pid: Optional[int]) -> None:
        """Update PTY information in the database session."""
        try:
            async with AsyncSessionLocal() as db:
                stmt = (
                    update(TerminalSession)
                    .where(TerminalSession.session_id == session_id)
                    .values(shell_pid=pid)
                )
                await db.execute(stmt)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update session PTY info: {e}")

    async def _update_session_terminal_size(self, session_id: str, cols: int, rows: int) -> None:
        """Update terminal size in the database session."""
        try:
            async with AsyncSessionLocal() as db:
                stmt = (
                    update(TerminalSession)
                    .where(TerminalSession.session_id == session_id)
                    .values(terminal_size={"cols": cols, "rows": rows})
                )
                await db.execute(stmt)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update session terminal size: {e}")

    async def shutdown(self) -> None:
        """Shutdown all PTY instances."""
        logger.info("Shutting down PTY service")

        await self.stop_monitoring()

        # Stop all instances
        tasks = []
        for session_id in list(self._instances.keys()):
            tasks.append(self.destroy_pty(session_id, force=True))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("PTY service shutdown complete")


# Global service instance
pty_service = PTYService()


async def get_pty_service() -> PTYService:
    """Dependency injection for PTY service."""
    return pty_service


# Convenience functions
async def create_pty_for_session(session_id: str, shell: str = "/bin/bash",
                                cols: int = 80, rows: int = 24,
                                cwd: str = "/", env: Optional[Dict[str, str]] = None) -> PTYInstance:
    """Create a PTY instance for a terminal session."""
    config = PTYConfig(
        shell=shell,
        cols=cols,
        rows=rows,
        cwd=cwd,
        env=env
    )
    return await pty_service.create_pty(session_id, config)


async def cleanup_pty_on_session_end(session_id: str) -> None:
    """Clean up PTY when a session ends."""
    await pty_service.destroy_pty(session_id)