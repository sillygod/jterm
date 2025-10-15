# Quickstart: Enhanced Media Support and Performance Optimization

**Feature**: 002-enhance-and-implement
**Prerequisites**: jterm running, database migrated, default user created

## Quick Test Scenarios

### 1. Ebook Viewing (bookcat command)

**Test PDF Viewing**:
```bash
# Create a test PDF (or use existing)
echo "This is a test PDF" > /tmp/test.txt
# Use a real PDF file instead, e.g.:
cp ~/Documents/sample.pdf /tmp/test.pdf

# In jterm terminal, run:
bookcat /tmp/test.pdf

# Expected: Modal opens showing PDF content
# Verify: Navigation buttons (prev/next page)
# Verify: Close button works
```

**Test EPUB Viewing**:
```bash
# Use a sample EPUB file
cp ~/Books/sample.epub /tmp/test.epub

# In jterm terminal:
bookcat /tmp/test.epub

# Expected: EPUB renders with HTML/CSS styling preserved
# Verify: Fonts, images, formatting intact
```

**Test Password-Protected PDF**:
```bash
# Create password-protected PDF (use PyPDF2 or existing file)
# In jterm terminal:
bookcat /tmp/protected.pdf

# Expected: Password prompt modal appears
# Enter password, click Submit
# Expected: PDF decrypts and displays
# Test incorrect password: Shows error, allows retry (max 3 attempts)
```

**Test File Size Limit**:
```bash
# Try file larger than 50MB
bookcat /tmp/large_book.pdf  # >50MB

# Expected: Error message "File exceeds 50MB limit"
```

**Test File Not Found**:
```bash
bookcat /nonexistent/file.pdf

# Expected: Clear error "File not found: /nonexistent/file.pdf"
```

### 2. Recording Playback Width Scaling

**Test Normal Width Recording** (80-120 columns):
```bash
# Create a recording with standard terminal width
# In jterm:
1. Start recording (click record button)
2. Run: ls -la
3. Run: ps aux | head
4. Stop recording

# Play back recording:
1. Click "Recordings" menu
2. Select recent recording
3. Expected: Terminal displays at full width (no scaling)
4. Verify: All text visible, no truncation
```

**Test Wide Recording** (>120 columns):
```bash
# Resize terminal to 150 columns before recording
1. Resize browser window to make terminal wider
2. Start recording
3. Run: ps aux  # Should show many columns
4. Run: docker ps  # Or any command with wide output
5. Stop recording

# Play back recording:
1. Open recording playback
2. Resize browser to narrower width
3. Expected: Terminal content scales down proportionally
4. Verify: All content visible (scaled), no horizontal scroll
5. Resize browser wider
6. Expected: Content scales up smoothly within 200ms
```

**Test Resize Performance**:
```bash
# Measure resize latency
1. Open a wide recording (>120 columns)
2. Open browser DevTools → Performance tab
3. Start recording performance
4. Resize browser window rapidly (drag edge)
5. Stop performance recording
6. Expected: Each resize event completes in <200ms
```

### 3. Performance Metrics Display

**Test Metrics Toggle**:
```bash
# In jterm interface:
1. Click Settings (gear icon)
2. Find "Show Performance Metrics" toggle
3. Enable toggle
4. Expected: Performance widget appears (top-right or sidebar)
5. Verify displays: CPU%, Memory MB, WebSocket count
6. Disable toggle
7. Expected: Widget disappears
```

**Test Metrics Refresh Interval**:
```bash
# In Settings:
1. Enable performance metrics
2. Set refresh interval to 3000ms (3 seconds)
3. Watch metrics widget
4. Expected: Numbers update every 3 seconds
5. Change interval to 10000ms (10 seconds)
6. Expected: Updates slow to every 10 seconds
```

**Test Metrics API**:
```bash
# Using curl or browser fetch
curl http://localhost:8000/api/performance/current

# Expected JSON:
{
  "cpu_percent": 4.2,
  "memory_mb": 256.8,
  "active_websockets": 2,
  "terminal_updates_per_sec": 8.5,
  "timestamp": "2025-10-09T10:30:00Z"
}

# Get historical data
curl "http://localhost:8000/api/performance/history?minutes=30"

# Expected: Array of snapshots from last 30 minutes
```

### 4. CPU Optimization Validation

**Test Idle CPU Usage**:
```bash
# Measure idle CPU after startup
1. Start jterm: uvicorn src.main:app
2. Open one terminal session in browser
3. Wait 5 minutes (no activity)
4. Check CPU in system monitor (Activity Monitor/top):
   ps aux | grep "python.*uvicorn"
5. Expected: CPU < 5% for idle jterm process
```

**Test Active Terminal CPU**:
```bash
# Measure CPU during normal use
1. Open jterm terminal
2. Run commands continuously:
   while true; do ls; sleep 1; done
3. Monitor CPU usage
4. Expected: CPU < 15% during active command execution
```

**Test Recording Playback CPU**:
```bash
# Measure CPU during playback
1. Open a long recording (5+ minutes)
2. Play recording at 1x speed
3. Monitor CPU usage
4. Expected: CPU < 25% during playback
```

**Test Multiple Sessions**:
```bash
# Test linear scaling (not exponential)
1. Open 1 terminal tab → Measure CPU (baseline)
2. Open 2 terminal tabs → Measure CPU (should be ~2x)
3. Open 3 terminal tabs → Measure CPU (should be ~3x)
4. Expected: CPU scales linearly, not exponentially
5. Verify: 3 sessions should be < 45% total (3 × 15%)
```

### 5. Integration Test Scenarios

**End-to-End Ebook Workflow**:
```bash
# Full workflow from file to display
1. Place PDF in filesystem: /home/user/doc.pdf
2. Run in terminal: bookcat /home/user/doc.pdf
3. Verify: File metadata stored in database:
   sqlite3 webterminal.db "SELECT * FROM ebook_metadata WHERE file_path LIKE '%doc.pdf%';"
4. Navigate to page 5 using UI controls
5. Close viewer
6. Re-open same file: bookcat /home/user/doc.pdf
7. Verify: Opens faster (cached metadata)
8. Check last_accessed timestamp updated
```

**Performance Monitoring Workflow**:
```bash
# End-to-end metrics collection
1. Enable performance metrics in UI
2. Run intensive command: find / -name "*.py" 2>/dev/null
3. Watch metrics widget update in real-time
4. Query database directly:
   sqlite3 webterminal.db "SELECT cpu_percent, timestamp FROM performance_snapshots ORDER BY timestamp DESC LIMIT 10;"
5. Verify: Snapshots captured during command execution
6. Wait 25 hours
7. Verify: Old snapshots auto-deleted (24h retention)
```

## Performance Benchmarks

Run these to validate performance requirements:

**PDF Rendering Speed**:
```bash
# Time PDF loading (10MB file)
1. Clear browser cache
2. Run: time bookcat /tmp/10mb_test.pdf
3. Measure time to first render
4. Expected: < 3 seconds

# EPUB rendering (5MB file)
1. Clear cache
2. Run: time bookcat /tmp/5mb_test.epub
3. Expected: < 2 seconds
```

**Page Navigation Speed**:
```bash
# Measure page turn latency
1. Open multi-page PDF (50+ pages)
2. Use browser DevTools → Performance
3. Click "Next Page" button
4. Measure time from click to new page render
5. Expected: < 500ms
```

**Recording Resize Latency**:
```bash
# Already tested above in section 2
# Verify: < 200ms per resize event
```

## Troubleshooting

**Ebook not displaying**:
- Check file path is absolute
- Verify file size < 50MB
- Check browser console for errors
- Verify foliate-js library loaded (DevTools → Network)

**Performance metrics not updating**:
- Verify toggle is enabled in settings
- Check WebSocket connection (DevTools → Network → WS)
- Verify psutil installed: `pip show psutil`
- Check backend logs for errors

**High CPU still observed**:
- Verify WebSocket ping interval is 60s (src/websockets/terminal_handler.py)
- Check terminal output debounce is active (100ms window)
- Profile with py-spy: `py-spy record --pid <pid> --duration 60`
- Compare to baseline flamegraph

**Recording playback not scaling**:
- Check CSS transform applied (DevTools → Elements → Computed)
- Verify recording dimensions available (API: `/api/recordings/{id}/dimensions`)
- Test window resize event firing
- Check debounce function (200ms delay)

## Success Criteria Checklist

After running all quickstart scenarios, verify:

- [ ] PDF files render in < 3s (10MB)
- [ ] EPUB files render in < 2s (5MB)
- [ ] Password-protected PDFs prompt and decrypt correctly
- [ ] Files > 50MB rejected with clear error
- [ ] Recording playback scales to fit viewport
- [ ] Recording resize completes in < 200ms
- [ ] Performance metrics toggle works
- [ ] Metrics refresh at configured interval
- [ ] Idle CPU < 5% after 5 minutes
- [ ] Active terminal CPU < 15%
- [ ] Recording playback CPU < 25%
- [ ] Multiple sessions scale linearly
- [ ] Database migrations applied successfully
- [ ] All contract tests pass
- [ ] Integration tests pass

**If all items checked**: Feature implementation validated ✅

---

**Last Updated**: 2025-10-09
**For**: jterm developers and QA testers
