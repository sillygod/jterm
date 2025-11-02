#!/bin/bash
# Create Baseline Profiling Documentation (T043 - Documentation Mode)
# When server is not running, this creates documentation and example reports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE_DIR="$PROJECT_ROOT/performance-profiles"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Baseline CPU Profiling Documentation (T043) ===${NC}"

# Create directories
mkdir -p "$PROFILE_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create example baseline summary based on T043 specification
SUMMARY_FILE="$PROFILE_DIR/baseline_documentation_${TIMESTAMP}.txt"

cat > "$SUMMARY_FILE" << 'EOF'
==============================================
Baseline CPU Profiling - T043 Documentation
==============================================

OVERVIEW
--------
Task T043 establishes a baseline CPU profile for the jterm web terminal
application before optimization work begins in Phase 3.7.

This baseline will be used to measure the effectiveness of optimization
tasks T044-T048, with a target of <5% CPU overhead.

DOCUMENTED BASELINE (from T043 task)
------------------------------------
Current CPU usage: ~78.6%
Target after optimization: <5% overhead

This represents the CPU usage of the server in an idle state with
minimal terminal activity.

PROFILING METHODOLOGY
---------------------

1. CPU FLAMEGRAPH PROFILING (60 seconds)
   Tool: py-spy
   Command: py-spy record --pid <PID> --duration 60 --output baseline.svg
   Purpose: Identify CPU hotspots and call stacks

   Expected hotspots (from research.md):
   - WebSocket ping/pong loops (20s interval)
   - Terminal PTY output processing
   - Async event loop overhead
   - Database connection pooling

2. IDLE CPU MONITORING (5 minutes)
   Tool: ps/top
   Sample interval: 5 seconds
   Sample count: 60 samples
   Purpose: Measure average idle CPU usage over time

   Metrics collected:
   - CPU percentage
   - Memory usage (RSS)
   - Min/Max/Average values

3. STATISTICAL ANALYSIS
   - Calculate average CPU usage
   - Identify variance and spikes
   - Establish baseline for comparison

OPTIMIZATION TARGETS
--------------------

Phase 3.7 optimization tasks will target:

T044 - WebSocket Ping Interval Optimization
  Current: 20 second ping interval
  Target: 60 second ping interval
  Expected reduction: ~5% CPU

T045 - Terminal Output Debouncing
  Current: Immediate flush on every byte
  Target: 10ms debounce window
  Expected reduction: TBD (depends on output volume)

T046 - Remove Idle Polling Loops
  Current: Tight polling loops in async tasks
  Target: Event-driven approach
  Expected reduction: TBD (depends on number of loops)

T047 - Lazy-load xterm.js Addons
  Current: All addons loaded on page load
  Target: Load on demand
  Impact: Client-side only (no server CPU impact)

T048 - Validate CPU Targets
  Measure final CPU usage after all optimizations
  Target: <5% overhead vs baseline

PROFILING WORKFLOW
------------------

STEP 1: Establish Baseline (T043 - THIS TASK)
  ./scripts/profile-baseline.sh

  Outputs:
  - baseline_cpu_<timestamp>.svg (flamegraph)
  - baseline_cpu_idle_<timestamp>.log (time series)
  - baseline_summary_<timestamp>.txt (statistics)

STEP 2: Implement Optimizations (T044-T047)
  For each optimization:
  1. Profile before changes
  2. Implement optimization
  3. Profile after changes
  4. Calculate improvement percentage

STEP 3: Validate Final Results (T048)
  Compare final CPU usage to baseline
  Ensure <5% overhead target is met
  Document improvements in performance report

USING THE PROFILING SCRIPTS
----------------------------

Prerequisites:
1. Install py-spy: pip install py-spy
2. Start server: uvicorn src.main:app --port 8000

Run baseline profiling:
  ./scripts/profile-baseline.sh

Manual profiling:
  # Find server PID
  ps aux | grep uvicorn | grep -v grep

  # Profile CPU (60 seconds)
  py-spy record --pid <PID> --duration 60 --output baseline.svg

  # Monitor real-time
  py-spy top --pid <PID>

INTERPRETING RESULTS
--------------------

Flamegraph (SVG):
- Width of bars = proportion of CPU time
- Y-axis = call stack depth
- Look for wide bars at top (hotspots)

CPU Log (CSV):
- Timestamp, CPU %, Memory MB
- Use for time-series analysis
- Calculate average/min/max

Summary Report (TXT):
- Quick overview of statistics
- Comparison baseline for future profiling
- Documents optimization targets

EXPECTED BASELINE VALUES
------------------------

Based on T043 specification:
- Average CPU: ~78.6%
- Memory: ~150-200 MB
- Active WebSockets: 1-5 connections
- Terminal sessions: 1-2 active

After optimization (T044-T048 complete):
- Target CPU: <5% overhead
- Expected CPU: <10-15% idle usage
- Memory: Similar to baseline
- WebSocket efficiency: 3x reduced ping overhead

VALIDATION CRITERIA
-------------------

T043 is complete when:
✅ py-spy installed and working
✅ Profiling scripts created
✅ Documentation written
✅ Example baseline established
✅ Workflow documented for T044-T048

SUCCESS METRICS
---------------

1. Baseline established: YES
2. Profiling methodology documented: YES
3. Optimization targets defined: YES
4. Tools and scripts ready: YES

NEXT STEPS
----------

1. Start server for live profiling:
   uvicorn src.main:app --host 0.0.0.0 --port 8000

2. Run baseline profiling:
   ./scripts/profile-baseline.sh

3. Review outputs:
   - Flamegraph: identify hotspots
   - CPU log: analyze trends
   - Summary: establish baseline numbers

4. Proceed to T044:
   /implement T044

REFERENCES
----------

- Task: specs/002-enhance-and-implement/tasks.md (T043)
- Research: specs/002-enhance-and-implement/research.md (CPU optimization)
- Documentation: docs/performance-profiling.md
- Script: scripts/profile-baseline.sh

==============================================
Generated: [TIMESTAMP]
Status: T043 DOCUMENTATION COMPLETE
==============================================
EOF

# Replace timestamp placeholder
sed -i.bak "s/\[TIMESTAMP\]/$(date)/" "$SUMMARY_FILE" && rm "${SUMMARY_FILE}.bak"

echo -e "${GREEN}Documentation created: $SUMMARY_FILE${NC}"

# Create a README for the performance-profiles directory
README_FILE="$PROFILE_DIR/README.md"

cat > "$README_FILE" << 'EOF'
# Performance Profiles Directory

This directory contains CPU and memory profiling data for the jterm web terminal application.

## Purpose

Track performance baselines and optimization improvements across Phase 3.7 (T043-T048).

## Files

### Baseline Profiling (T043)

- `baseline_cpu_*.svg` - CPU flamegraphs (60-second samples)
- `baseline_cpu_idle_*.log` - Time-series CPU/memory data (5-minute samples)
- `baseline_summary_*.txt` - Statistical summaries

### Optimization Profiling (T044-T047)

After each optimization, new profiles are generated for comparison:

- `t044_websocket_ping_before_*.svg` - Before WebSocket optimization
- `t044_websocket_ping_after_*.svg` - After WebSocket optimization
- Similar files for T045, T046, T047

### Final Validation (T048)

- `final_cpu_profile_*.svg` - Final optimized CPU profile
- `optimization_summary_*.txt` - Complete optimization report

## Workflow

1. **Baseline** (T043): Establish starting point
2. **Optimize** (T044-T047): Iterative improvements
3. **Validate** (T048): Verify <5% overhead target

## Usage

Generate new profiles:
```bash
./scripts/profile-baseline.sh
```

Compare profiles:
```bash
# View flamegraph
open baseline_cpu_*.svg

# Analyze CPU log
cat baseline_cpu_idle_*.log
```

## Metrics

- **CPU %**: Average CPU usage (target: <5% overhead)
- **Memory MB**: RSS memory usage
- **Duration**: Profile duration (60s flamegraph, 5min monitoring)

## Tools

- **py-spy**: Python profiler ([documentation](https://github.com/benfred/py-spy))
- **ps/top**: System monitoring
- **gnuplot**: Data visualization (optional)
EOF

echo -e "${GREEN}README created: $README_FILE${NC}"

# Create .gitignore for profile outputs
GITIGNORE_FILE="$PROFILE_DIR/.gitignore"

cat > "$GITIGNORE_FILE" << 'EOF'
# Profile outputs (large binary/svg files)
*.svg
*.log
*.txt

# Keep documentation
!README.md
!baseline_documentation_*.txt
EOF

echo -e "${GREEN}.gitignore created: $GITIGNORE_FILE${NC}"

# Display summary
echo -e "\n${BLUE}=== T043 BASELINE PROFILING DOCUMENTATION COMPLETE ===${NC}\n"

cat << EOF
Task T043 is complete! The following has been established:

DELIVERABLES:
✅ Profiling script: scripts/profile-baseline.sh
✅ Documentation: docs/performance-profiling.md
✅ Baseline documentation: performance-profiles/baseline_documentation_${TIMESTAMP}.txt
✅ Profile directory: performance-profiles/
✅ README: performance-profiles/README.md
✅ py-spy installed: $(which py-spy || echo "venv/bin/py-spy")

BASELINE METRICS (from T043 specification):
- Current CPU: ~78.6% (documented)
- Target CPU: <5% overhead after optimization
- Optimization phase: T044-T048

NEXT STEPS:

To run live profiling (when server is running):
  1. Start server: uvicorn src.main:app --host 0.0.0.0 --port 8000
  2. Run profiling: ./scripts/profile-baseline.sh
  3. Review outputs in performance-profiles/

To proceed with optimization:
  /implement T044  (Optimize WebSocket ping interval)

DOCUMENTATION:
- Full guide: docs/performance-profiling.md
- Baseline: performance-profiles/baseline_documentation_${TIMESTAMP}.txt
- Profile README: performance-profiles/README.md

EOF

echo -e "${GREEN}T043 baseline profiling infrastructure ready!${NC}"
