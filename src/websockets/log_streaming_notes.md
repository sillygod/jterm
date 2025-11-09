# WebSocket Log Streaming Notes
**T020: Future Enhancement for Real-Time Log Following**

## Current Implementation Status

The logcat viewer currently supports:
- ✅ HTTP streaming via `/api/logs/stream` endpoint (NDJSON format)
- ✅ Async file reading with `aiofiles`
- ✅ Memory-efficient streaming for large files
- ✅ Filter and search while streaming

## Future Enhancement: WebSocket Real-Time Following (tail -f mode)

### Requirements
To implement true real-time log following (similar to `tail -f`), the following would be needed:

1. **File Watching Library**
   ```bash
   pip install watchdog>=3.0.0
   ```

2. **WebSocket Message Handler**
   Add a new message type to `terminal_handler.py`:
   ```python
   async def handle_log_stream_request(self, session_id: str, file_path: str):
       """Stream log file updates via WebSocket"""
       from watchdog.observers import Observer
       from watchdog.events import FileSystemEventHandler

       # Watch file for modifications
       # Stream new lines to WebSocket as they appear
   ```

3. **Client-Side Integration**
   Update `log-viewer.js` to:
   - Connect to WebSocket for real-time updates
   - Append new log entries to the list
   - Auto-scroll to bottom (with option to pin)

### Design Considerations

**Performance:**
- Limit number of concurrent file watchers
- Debounce file change events (avoid flooding on rapid writes)
- Buffer new entries before sending to client

**Resource Management:**
- Stop watching when viewer is closed
- Cleanup file watchers on WebSocket disconnect
- Handle log rotation gracefully

**User Experience:**
- Visual indicator when following is active
- Button to pause/resume following
- Option to jump to bottom or stay at current position

### Implementation Sketch

```python
# In src/services/log_streaming_service.py (future)
class LogStreamingService:
    def __init__(self):
        self.observers = {}  # file_path -> Observer
        self.callbacks = {}  # file_path -> List[callback]

    async def watch_file(self, file_path: str, callback):
        """Watch file for changes and call callback with new lines"""
        if file_path not in self.observers:
            observer = Observer()
            handler = LogFileHandler(callback)
            observer.schedule(handler, path=file_path, recursive=False)
            observer.start()
            self.observers[file_path] = observer

    async def stop_watching(self, file_path: str):
        """Stop watching file"""
        if file_path in self.observers:
            self.observers[file_path].stop()
            del self.observers[file_path]
```

### Alternative: Polling-Based Approach

For simpler implementation without `watchdog`:

```python
async def poll_log_file(file_path: str, interval: float = 1.0):
    """Poll file for new lines (simple tail -f alternative)"""
    last_position = 0

    while True:
        async with aiofiles.open(file_path, 'r') as f:
            await f.seek(last_position)
            new_lines = await f.readlines()
            last_position = await f.tell()

            for line in new_lines:
                yield parse_line(line)

        await asyncio.sleep(interval)
```

## Current Workaround

Users can manually refresh the log viewer or use the existing HTTP streaming endpoint which loads the file once. For most use cases, this is sufficient.

## Priority

**Low Priority** - The current implementation covers the core requirements. Real-time following is a nice-to-have enhancement for future versions.

## References

- Watchdog documentation: https://python-watchdog.readthedocs.io/
- Alternative: `aiofiles` with `asyncio.sleep()` polling
- WebSocket streaming example in `src/websockets/terminal_handler.py`
