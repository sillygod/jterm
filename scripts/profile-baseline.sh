#!/bin/bash
# Baseline CPU Profiling Script (T043)
# Captures CPU profile for performance optimization baseline

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="$PROJECT_ROOT/performance-profiles"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Baseline CPU Profiling (T043) ===${NC}"
echo "Profile directory: $PROFILE_DIR"

# Create profile directory
mkdir -p "$PROFILE_DIR"

# Check if server is running
echo -e "\n${YELLOW}Checking if server is running...${NC}"
SERVER_PID=$(ps aux | grep "uvicorn.*main:app" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$SERVER_PID" ]; then
    echo -e "${RED}ERROR: Server is not running${NC}"
    echo "Please start the server first:"
    echo "  uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"
    exit 1
fi

echo -e "${GREEN}Server PID: $SERVER_PID${NC}"

# 1. CPU Profiling with py-spy (60 seconds)
echo -e "\n${YELLOW}Step 1: Running py-spy CPU profiling (60 seconds)...${NC}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FLAMEGRAPH_FILE="$PROFILE_DIR/baseline_cpu_${TIMESTAMP}.svg"

py-spy record \
    --pid "$SERVER_PID" \
    --duration 60 \
    --rate 100 \
    --output "$FLAMEGRAPH_FILE" \
    --format flamegraph \
    --subprocesses

echo -e "${GREEN}Flamegraph saved: $FLAMEGRAPH_FILE${NC}"

# 2. Capture idle CPU usage (5 minutes)
echo -e "\n${YELLOW}Step 2: Measuring idle CPU usage (5 minutes)...${NC}"
echo "Sampling CPU every 5 seconds for 5 minutes..."

CPU_LOG="$PROFILE_DIR/baseline_cpu_idle_${TIMESTAMP}.log"
START_TIME=$(date +%s)
END_TIME=$((START_TIME + 300)) # 5 minutes

echo "# Baseline CPU Usage - Idle State" > "$CPU_LOG"
echo "# Timestamp, CPU %, Memory MB" >> "$CPU_LOG"
echo "# Started at: $(date)" >> "$CPU_LOG"
echo "" >> "$CPU_LOG"

SAMPLE_COUNT=0
CPU_SUM=0
MEM_SUM=0

while [ $(date +%s) -lt $END_TIME ]; do
    # Get CPU and memory for the process
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        CPU=$(ps -p "$SERVER_PID" -o %cpu | tail -1 | xargs)
        MEM=$(ps -p "$SERVER_PID" -o rss | tail -1 | xargs)
        MEM_MB=$(echo "scale=2; $MEM / 1024" | bc)
    else
        # Linux
        CPU=$(ps -p "$SERVER_PID" -o %cpu --no-headers)
        MEM=$(ps -p "$SERVER_PID" -o rss --no-headers)
        MEM_MB=$(echo "scale=2; $MEM / 1024" | bc)
    fi

    TIMESTAMP_NOW=$(date +%Y-%m-%d\ %H:%M:%S)
    echo "$TIMESTAMP_NOW, $CPU, $MEM_MB" >> "$CPU_LOG"

    # Calculate running average
    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    CPU_SUM=$(echo "$CPU_SUM + $CPU" | bc)
    MEM_SUM=$(echo "$MEM_SUM + $MEM_MB" | bc)

    # Progress indicator
    ELAPSED=$(($(date +%s) - START_TIME))
    PROGRESS=$((ELAPSED * 100 / 300))
    echo -ne "\rProgress: $PROGRESS% (${ELAPSED}s / 300s) - Current CPU: ${CPU}%   "

    sleep 5
done

echo -e "\n${GREEN}CPU log saved: $CPU_LOG${NC}"

# 3. Calculate statistics
echo -e "\n${YELLOW}Step 3: Calculating statistics...${NC}"

AVG_CPU=$(echo "scale=2; $CPU_SUM / $SAMPLE_COUNT" | bc)
AVG_MEM=$(echo "scale=2; $MEM_SUM / $SAMPLE_COUNT" | bc)

# Find min/max CPU
MIN_CPU=$(grep -v "^#" "$CPU_LOG" | awk -F, '{print $2}' | sort -n | head -1 | xargs)
MAX_CPU=$(grep -v "^#" "$CPU_LOG" | awk -F, '{print $2}' | sort -n | tail -1 | xargs)

# 4. Create summary report
SUMMARY_FILE="$PROFILE_DIR/baseline_summary_${TIMESTAMP}.txt"

cat > "$SUMMARY_FILE" << EOF
==============================================
Baseline CPU Profiling Summary (T043)
==============================================
Date: $(date)
Server PID: $SERVER_PID
Profile Duration: 5 minutes (300 seconds)
Sample Count: $SAMPLE_COUNT samples
Sample Interval: 5 seconds

CPU USAGE STATISTICS
--------------------
Average CPU: ${AVG_CPU}%
Minimum CPU: ${MIN_CPU}%
Maximum CPU: ${MAX_CPU}%

MEMORY USAGE STATISTICS
-----------------------
Average Memory: ${AVG_MEM} MB

FILES GENERATED
---------------
1. Flamegraph: $FLAMEGRAPH_FILE
2. CPU Log: $CPU_LOG
3. Summary: $SUMMARY_FILE

BASELINE METRICS (for T043 validation)
---------------------------------------
Current baseline CPU: ${AVG_CPU}%
Target after optimization: <5% overhead

NOTES
-----
- This baseline represents idle server CPU usage
- Subsequent optimizations (T044-T048) will target this baseline
- Target: Reduce CPU overhead to <5% of idle baseline
- Optimization tasks:
  * T044: Optimize WebSocket ping interval (60s)
  * T045: Implement terminal output debouncing
  * T046: Remove idle polling loops
  * T047: Lazy-load xterm.js addons
  * T048: Validate CPU targets (<5% overhead)

==============================================
EOF

echo -e "${GREEN}Summary saved: $SUMMARY_FILE${NC}"

# 5. Display summary
echo -e "\n${GREEN}=== BASELINE PROFILING COMPLETE ===${NC}"
echo ""
cat "$SUMMARY_FILE"

# 6. Suggestions
echo -e "\n${YELLOW}NEXT STEPS:${NC}"
echo "1. Review flamegraph: open $FLAMEGRAPH_FILE"
echo "2. Review CPU log: cat $CPU_LOG"
echo "3. Proceed with optimization tasks:"
echo "   /implement T044 (Optimize WebSocket ping interval)"
echo ""
echo -e "${GREEN}Baseline profiling complete!${NC}"
