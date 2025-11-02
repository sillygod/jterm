#!/bin/bash
# Script to kill orphan PTY/bash processes left by jterm

echo "=== Killing Orphan jterm Processes ==="
echo ""

# Find the main jterm server process
JTERM_PID=$(ps aux | grep "[j]term/venv/bin/python3.*uvicorn" | awk '{print $2}' | head -1)

if [ -z "$JTERM_PID" ]; then
    echo "No jterm server process found."
    echo "Server is not running."
    exit 0
fi

echo "✅ Found jterm server: PID $JTERM_PID"
echo ""

# Find child processes (bash shells spawned by PTY)
CHILD_PIDS=$(pgrep -P $JTERM_PID 2>/dev/null)

if [ -z "$CHILD_PIDS" ]; then
    echo "✅ No orphan child processes found."
    echo "All PTY processes have been cleaned up properly."
    exit 0
fi

echo "⚠️  Found orphan child processes:"
for PID in $CHILD_PIDS; do
    PROC_INFO=$(ps -p $PID -o pid,ppid,command | tail -1)
    echo "   $PROC_INFO"
done

echo ""
read -p "Kill these orphan processes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    for PID in $CHILD_PIDS; do
        kill -9 $PID 2>/dev/null && echo "✅ Killed PID $PID"
    done
    echo ""
    echo "✅ All orphan processes killed"
else
    echo "Skipped killing processes"
fi
