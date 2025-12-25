# Debug: WebSocket Stuck on "CONNECTING..."

**Issue**: Status bar shows "CONNECTING..." instead of "CONNECTED"
**Affected**: Tauri Desktop Application

---

## Diagnosis Steps

### 1. Check Browser Console (Most Important!)

**How to open console in Tauri**:
- **macOS**: Right-click → "Inspect Element" or `Cmd+Option+I`
- **Windows**: Right-click → "Inspect" or `F12`
- **Linux**: Right-click → "Inspect" or `Ctrl+Shift+I`

**What to look for**:
```
❌ WebSocket connection to 'ws://localhost:XXXX/ws/terminal' failed: ...
❌ Failed to construct 'WebSocket': ...
❌ Error in connection establishment: ...
```

### 2. Check Python Backend Status

**Verify backend is running**:
```bash
# In terminal
ps aux | grep "jterm-backend" | grep -v grep

# Should show something like:
# jing  12345  ... jterm-backend-aarch64-apple-darwin
```

**Check backend port**:
```bash
# Check what port Python backend is listening on
lsof -i TCP | grep jterm-backend

# Should show something like:
# jterm-bac 12345 jing  TCP localhost:8001 (LISTEN)
```

### 3. Possible Causes & Solutions

#### Cause 1: WebSocket Endpoint Not Ready

**Symptom**: Backend started but WebSocket endpoint not initialized yet

**Solution**: Add delay before connecting WebSocket

```javascript
// In terminal.js, modify connectWebSocket():
connectWebSocket() {
    // Add small delay to ensure backend is fully ready
    setTimeout(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

        console.log('[DEBUG] Connecting to WebSocket:', wsUrl);
        this.websocket = new WebSocket(wsUrl);

        // ... rest of code
    }, 500); // 500ms delay
}
```

#### Cause 2: Port Mismatch in iframe

**Symptom**: iframe loaded from different port than expected

**Debug**: Add logging to see actual URLs

```javascript
// Add to desktop.js after iframe loads:
console.log('[DEBUG] iframe location:', iframe.contentWindow.location.href);
console.log('[DEBUG] Expected backend port:', backendPort);
```

**Fix**: Ensure WebSocket uses correct port from Tauri

```javascript
// In terminal.js, check if running in Tauri:
connectWebSocket() {
    let wsUrl;

    if (window.__TAURI_DESKTOP__) {
        // In Tauri, explicitly use the backend port
        const backendPort = window.location.port || '8000';
        wsUrl = `ws://localhost:${backendPort}/ws/terminal`;
        console.log('[TAURI] Using WebSocket URL:', wsUrl);
    } else {
        // Regular web mode
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/ws/terminal`;
    }

    this.websocket = new WebSocket(wsUrl);
    // ... rest of code
}
```

#### Cause 3: CORS or Security Policy

**Symptom**: Browser blocks WebSocket connection

**Check**: Look for CORS errors in console

**Fix**: Ensure FastAPI allows WebSocket connections

```python
# In src/main.py, check CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Cause 4: Backend Still Processing (from I/O fixes)

**Symptom**: Backend is slow to start after rebuilding

**Solution**: Wait a bit longer or check backend logs

```bash
# Check if backend is still initializing
tail -f ~/Library/Logs/jterm/backend.log  # macOS
# or wherever Tauri logs Python backend output
```

---

## Quick Fix: Add Debug Logging

**File**: `static/js/terminal.js`

Add extensive logging to `connectWebSocket()`:

```javascript
connectWebSocket() {
    console.log('[WebSocket] Attempting connection...');
    console.log('[WebSocket] Protocol:', window.location.protocol);
    console.log('[WebSocket] Host:', window.location.host);
    console.log('[WebSocket] Full URL:', window.location.href);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

    console.log('[WebSocket] Final WS URL:', wsUrl);
    console.log('[WebSocket] Creating WebSocket instance...');

    this.websocket = new WebSocket(wsUrl);
    console.log('[WebSocket] WebSocket readyState:', this.websocket.readyState);
    // 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED

    this.websocket.onopen = (event) => {
        console.log('[WebSocket] ✅ Connected successfully!', event);
        this.isConnected = true;
        this.updateConnectionStatus('connected');
        this.requestSession();
    };

    this.websocket.onerror = (event) => {
        console.error('[WebSocket] ❌ Error occurred:', event);
        console.error('[WebSocket] Error type:', event.type);
        console.error('[WebSocket] Error target:', event.target);
        this.updateConnectionStatus('error');
    };

    this.websocket.onclose = (event) => {
        console.log('[WebSocket] Connection closed:', {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
        });
        this.isConnected = false;
        this.updateConnectionStatus('disconnected');

        // Attempt to reconnect
        setTimeout(() => {
            console.log('[WebSocket] Attempting reconnection...');
            if (!this.isConnected) {
                this.connectWebSocket();
            }
        }, 3000);
    };
}
```

---

## Most Likely Solution

Based on the symptoms, the most likely cause is that **WebSocket is trying to connect before the backend is fully ready**.

**Recommended fix**:

1. **Rebuild Python backend** with I/O fixes:
   ```bash
   ./scripts/build-python.sh
   ```

2. **Add connection retry logic** to `static/js/terminal.js`:

```javascript
connectWebSocket(retryCount = 0) {
    const MAX_RETRIES = 5;
    const RETRY_DELAY = 2000; // 2 seconds

    console.log(`[WebSocket] Connection attempt ${retryCount + 1}/${MAX_RETRIES}`);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

    this.websocket = new WebSocket(wsUrl);

    this.websocket.onopen = (event) => {
        console.log('[WebSocket] ✅ Connected!');
        this.isConnected = true;
        this.updateConnectionStatus('connected');
        this.requestSession();
    };

    this.websocket.onerror = (event) => {
        console.error('[WebSocket] Connection error:', event);

        // Don't update status to 'error' immediately, might just be connecting
        if (retryCount < MAX_RETRIES) {
            console.log(`[WebSocket] Will retry in ${RETRY_DELAY}ms...`);
        } else {
            this.updateConnectionStatus('error');
            console.error('[WebSocket] Max retries reached. Giving up.');
        }
    };

    this.websocket.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        this.isConnected = false;

        // Retry connection if not at max retries
        if (retryCount < MAX_RETRIES && !event.wasClean) {
            setTimeout(() => {
                this.connectWebSocket(retryCount + 1);
            }, RETRY_DELAY);
        } else {
            this.updateConnectionStatus('disconnected');
        }
    };
}
```

---

## Testing Steps

1. **Open Tauri app**
2. **Open browser console** (`Cmd+Option+I` on macOS)
3. **Look for WebSocket logs**:
   - ✅ `[WebSocket] ✅ Connected!` → Success!
   - ❌ `[WebSocket] Connection error:` → Need to investigate

4. **Check network tab**:
   - Filter for "WS" (WebSocket)
   - Look for `/ws/terminal` connection
   - Check status (should be "101 Switching Protocols")

---

## Next Steps

**If still stuck on "CONNECTING..."**:

1. Share the browser console output
2. Check if Python backend is actually running
3. Verify the port Python backend is listening on
4. Try restarting the Tauri app

**Quick test without Tauri**:

```bash
# Start backend manually
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Open browser to http://localhost:8000
# Check if WebSocket connects successfully
```

If it works in browser but not in Tauri, the issue is specific to Tauri's iframe setup.
