#!/bin/bash
# Test script to measure idle CPU usage after optimizations

echo "=== CPU Idle Test for T044-T047 Optimizations ==="
echo ""
echo "Instructions:"
echo "1. Make sure the jterm server is running"
echo "2. Open ONE terminal tab in the browser"
echo "3. Do NOT type anything or run any commands"
echo "4. Stop any active recordings"
echo "5. Wait for this script to complete (5 minutes)"
echo ""
echo "This script will monitor CPU usage every 30 seconds for 5 minutes"
echo ""

# Find the jterm Python process
JTERM_PID=$(ps aux | grep "[j]term/venv/bin/python3" | awk '{print $2}')

if [ -z "$JTERM_PID" ]; then
    echo "❌ jterm process not found!"
    echo "Make sure the server is running: uvicorn src.main:app"
    exit 1
fi

echo "✅ Found jterm process: PID $JTERM_PID"
echo ""
echo "Monitoring CPU for 5 minutes (10 samples, 30s apart)..."
echo ""
echo "Time   | CPU%  | Memory MB | Context Switches | Unix Syscalls"
echo "-------|-------|-----------|------------------|---------------"

for i in {1..10}; do
    # Get current time
    TIMESTAMP=$(date +"%H:%M:%S")

    # Get CPU and memory using ps
    STATS=$(ps -p $JTERM_PID -o %cpu,rss | tail -1)
    CPU=$(echo $STATS | awk '{print $1}')
    MEM_KB=$(echo $STATS | awk '{print $2}')
    MEM_MB=$((MEM_KB / 1024))

    # Get context switches and system calls (macOS specific)
    if command -v lsof &> /dev/null; then
        # Use activity monitor style stats
        PROC_INFO=$(ps -p $JTERM_PID -o utime,stime 2>/dev/null)
    fi

    printf "%s | %5.2f | %7d MB | %-16s | %-13s\n" "$TIMESTAMP" "$CPU" "$MEM_MB" "N/A" "N/A"

    if [ $i -lt 10 ]; then
        sleep 30
    fi
done

echo ""
echo "=== Analysis ==="
echo ""
echo "Expected Results:"
echo "  - Idle CPU: <5% (target from T046)"
echo "  - Active CPU (with terminal I/O): <15%"
echo "  - Recording playback: <25%"
echo ""
echo "If CPU is still high:"
echo "  1. Check for active terminal commands (ctrl+c to stop)"
echo "  2. Check for active recordings (stop recording)"
echo "  3. Check for background processes in terminal"
echo "  4. Review browser console for JavaScript errors"
echo ""
echo "Current optimizations applied:"
echo "  ✅ T044: WebSocket ping (30s→60s)"
echo "  ✅ T045: Terminal output debouncing (100ms)"
echo "  ✅ T046: Polling removal (PTY: 0.5s, Recording: 10s)"
echo "  ✅ T047: Lazy-load xterm.js addons"
echo ""
