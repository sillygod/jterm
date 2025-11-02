# Missing Components in 002-enhance-and-implement

**Date**: 2025-10-27
**Status**: Gap Identified - bookcat command incomplete

## Issue: bookcat Command Not Functional

### What Exists ✅
1. **Backend API** (`src/api/ebook_endpoints.py`):
   - POST `/api/ebooks/process` - Process ebook file
   - GET `/api/ebooks/{id}/content` - Retrieve content
   - POST `/api/ebooks/{id}/decrypt` - Decrypt password-protected PDF
   - GET `/api/ebooks/metadata/{hash}` - Get cached metadata

2. **Backend Service** (`src/services/ebook_service.py`):
   - PDF/EPUB file validation
   - Metadata extraction
   - Password decryption for PDFs
   - File caching

3. **Frontend Viewer** (`templates/components/ebook_viewer.html` + `static/js/ebook-viewer.js`):
   - Modal viewer component
   - foliate-js integration
   - Page navigation controls

4. **Command Script** (`bin/bookcat`):
   - Shell script accepting file path
   - File validation
   - Sends OSC sequence: `\033]1338;ViewEbook=<path>\007`

### What's Missing ❌

**OSC Sequence Handler** - The critical glue layer that:
1. Detects OSC sequence `\033]1338;ViewEbook=<path>` in terminal output
2. Intercepts the sequence before it reaches the terminal display
3. Extracts the file path
4. Calls the ebook API to process the file
5. Sends frontend message to open the viewer modal

### Current Behavior

When user runs `bookcat file.pdf`:
1. ✅ Script executes, validates file
2. ✅ Sends OSC sequence `\033]1338;ViewEbook=/path/to/file.pdf\007`
3. ❌ **Sequence not detected** - appears as garbled text in terminal
4. ❌ Viewer modal never opens
5. Result: Command appears "not found" or produces garbled output

### Required Implementation

**File**: `src/services/pty_service.py` or `src/websockets/terminal_handler.py`

**Logic Needed**:
```python
# In PTY output processing loop
async def _process_output(self, data: bytes) -> bytes:
    """Process PTY output, intercept OSC sequences."""
    text = data.decode('utf-8', errors='replace')

    # Check for ebook viewer OSC sequence
    # Pattern: \033]1338;ViewEbook=<filepath>\007
    if '\033]1338;ViewEbook=' in text:
        # Extract file path
        import re
        match = re.search(r'\033\]1338;ViewEbook=([^\007]+)\007', text)
        if match:
            file_path = match.group(1)

            # Call ebook API to process file
            await self._trigger_ebook_viewer(file_path)

            # Remove OSC sequence from output
            text = re.sub(r'\033\]1338;ViewEbook=[^\007]+\007', '', text)

    return text.encode('utf-8')

async def _trigger_ebook_viewer(self, file_path: str):
    """Trigger ebook viewer via WebSocket."""
    # Send WebSocket message to frontend
    await self.websocket_manager.send_message(
        self.connection_id,
        "ebook_viewer",
        {"file_path": file_path}
    )
```

**Frontend WebSocket Handler** (`static/js/terminal.js` or `ebook-viewer.js`):
```javascript
// Listen for ebook viewer messages
socket.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'ebook_viewer') {
        // Call API to process file
        fetch('/api/ebooks/process', {
            method: 'POST',
            body: JSON.stringify({file_path: msg.data.file_path})
        })
        .then(r => r.json())
        .then(result => {
            // Open viewer modal with result.ebook_id
            openEbookViewer(result.ebook_id);
        });
    }
});
```

### Similar Implementation Examples

Check how other media commands work:
- `imgcat` → OSC sequence `\033]1337;ViewImage=`
- `vidcat` → OSC sequence (check existing implementation)
- Pattern should be similar for `bookcat`

**Action**: Search `src/` for existing OSC sequence handlers to understand the pattern, then implement for ebook viewer.

### Impact

**Current Status**: Ebook feature is **85% complete**
- ✅ Backend fully implemented (API + service)
- ✅ Frontend viewer fully implemented
- ✅ Command script created
- ❌ Integration layer (OSC handler) missing

**User Impact**: Cannot use `bookcat` command in terminal - appears as "command not found" or garbled output.

### Resolution

**STATUS**: ✅ RESOLVED - 2025-10-27

Implemented OSC sequence detection and handling across the stack:

1. ✅ **PTY Service** (`src/services/pty_service.py`):
   - Added OSC pattern matching with regex
   - Created `_process_osc_sequences()` method
   - Added `register_osc_callback()` method
   - Integrated OSC processing into output buffer flush

2. ✅ **Terminal Handler** (`src/websockets/terminal_handler.py`):
   - Registered ebook OSC callback on session creation
   - Sends WebSocket message when OSC sequence detected

3. ✅ **Frontend** (`static/js/terminal.js`):
   - Added `ebook_viewer` message handler
   - Created `handleEbookViewer()` method
   - Calls ebook API and opens viewer modal

4. ✅ **Command Script** (`bin/bookcat`):
   - Created executable shell script
   - Sends OSC sequence: `\033]1338;ViewEbook=<path>\007`

5. ✅ **Welcome Message** (`src/websockets/terminal_handler.py`):
   - Added `bookcat` to media commands list

### Testing

**To test** (after server restart):
```bash
# 1. Restart server
# 2. Open terminal in browser
# 3. Run: bookcat /path/to/file.pdf
# Expected: Modal viewer opens with PDF
```

---

**Reported**: 2025-10-27
**Resolved**: 2025-10-27 (same day)
**Priority**: High (blocks ebook viewer feature from being usable)
**Resolution Time**: ~1 hour
**Status**: ✅ COMPLETE - Ready for testing
