# T046 Critical Fix: Select Timeout Bug

**Date**: 2025-10-31
**Issue**: CPU regression from 0.08% to 38-40% when browser connected
**Status**: ✅ RESOLVED

## Problem Summary

After implementing T044-T047 optimizations, idle CPU without browser was excellent (0.08%). However, when a browser connected with a single idle terminal tab, CPU jumped to **38-40% and stayed there constantly**.

## Root Cause Analysis

### Investigation Process

1. **Initial hypothesis**: Thought it was the busy loop in timeout handler after T046 changes
   - Changed timeout from 1.0s back to 0.1s - **NO EFFECT** (CPU still 38%)
   - This ruled out the loop frequency as the issue

2. **Profiling with macOS `sample` tool**:
   ```bash
   sample <pid> 5 -file /tmp/jterm-sample.txt
   ```

   **Key findings from profiling**:
   - 64% time in `uv__io_poll → kevent` (GOOD - event loop waiting)
   - **26% time in `uv__run_idle → cb_idle_callback`** (BAD - continuous idle callbacks)
   - This indicated something was constantly scheduling async tasks

3. **Analyzed `_read_pty_output()` function**:
   ```python
   def try_read():
       # Check if data is available
       rlist, _, _ = select.select([self.process.fd], [], [], 0)  # ← PROBLEM!
       if rlist:
           data = os.read(self.process.fd, 1024)
           return data
       return b""

   data = await loop.run_in_executor(None, try_read)
   ```

### The Bug

**Line 400**: `select.select([fd], [], [], 0)` with **timeout=0**

This created a **busy-wait loop**:
1. Main loop calls `_read_pty_output()` every 0.1s
2. Each call schedules a thread pool task
3. Thread immediately calls `select()` with timeout=0
4. `select()` returns instantly without blocking (no data available)
5. Thread completes, returns to event loop
6. Loop schedules another task 0.1s later
7. **Repeat forever → 10 thread pool tasks/second + 10 syscalls/second = 38% CPU!**

## The Fix

Changed select timeout from `0` to `0.05` (50ms):

```python
# Before (line 400):
rlist, _, _ = select.select([self.process.fd], [], [], 0)

# After (line 401):
rlist, _, _ = select.select([self.process.fd], [], [], 0.05)
```

## Why This Works

### Timeout=0 (Busy-wait)
- `select()` returns **immediately** whether or not data is available
- No blocking, just polling
- CPU constantly schedules tasks and makes syscalls
- High overhead: thread pool scheduling + context switches + syscalls

### Timeout=0.05 (Kernel blocking)
- `select()` **blocks in kernel space** for up to 50ms
- When data arrives, kernel **immediately wakes** the select call (no 50ms delay!)
- When no data, thread sleeps in kernel (true idle, near-zero CPU)
- Low overhead: efficient kernel-level I/O multiplexing

### Why No Latency Impact

The 50ms timeout does **NOT** mean 50ms delay when data arrives:
- When PTY writes data → kernel detects fd is readable
- Kernel immediately unblocks select() (typically <1ms)
- Data is read and sent to terminal
- User experiences no perceptible delay

The timeout only matters when **no data arrives** - it allows the thread to sleep efficiently.

## Performance Impact

### Before Fix
- **Idle CPU**: 38-40% (constant)
- **Thread pool tasks**: 10/second
- **Select syscalls**: 10/second (all returning immediately)
- **Event loop**: Continuous idle callbacks (26% CPU)

### After Fix
- **Idle CPU**: <5% (target met!)
- **Thread pool tasks**: ~20/second max, but most **block** in kernel
- **Select syscalls**: Block efficiently, wake on data
- **Event loop**: True idle state, minimal callbacks

### Measurement
```bash
# 5-minute test with idle browser
Time   | CPU%  | Memory MB
-------|-------|----------
Before | 38-40%|    26 MB
After  | <5%   |    26 MB
```

## Key Learnings

1. **Polling vs Blocking**: Always prefer blocking system calls (timeout>0) over polling (timeout=0)
2. **Thread Pool Overhead**: Even "lightweight" thread pool tasks add up at high frequency
3. **Profiling Tools**: macOS `sample` tool excellent for identifying CPU hotspots
4. **Kernel Efficiency**: Let the kernel do the waiting - it's far more efficient than userspace polling
5. **Async I/O Pattern**: `select()` with timeout>0 is the correct pattern for async I/O

## Related Optimizations

This fix complements the other T046 optimizations:
- ✅ T044: WebSocket ping 30s → 60s
- ✅ T045: Terminal output debouncing (100ms window)
- ✅ T046 (original): PTY termination polling 0.1s → 0.5s
- ✅ **T046 (critical fix)**: Select timeout 0 → 0.05s ← **This was the main issue!**
- ✅ T047: Lazy-load xterm.js addons

## Files Modified

- `src/services/pty_service.py` line 401: Changed select timeout parameter

## Validation

- ✅ CPU usage: 38-40% → <5% with idle browser
- ✅ Terminal responsiveness: No perceptible latency
- ✅ T046 target: <5% idle CPU achieved
- ✅ Browser idle test: Passed (5-minute monitoring)

## References

- **man select(2)**: System call documentation
- **T046 specification**: Original polling removal task
- **T048 validation**: CPU optimization targets

---

**Conclusion**: The `select()` timeout=0 bug was the **true root cause** of the 38% CPU usage. Changing to timeout=0.05s enables efficient kernel-space blocking while maintaining responsive terminal I/O. This fix, combined with T044-T047 optimizations, achieves the <5% idle CPU target.
