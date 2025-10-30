# Performance Profiling Guide

This guide explains how to profile CPU usage for the jterm web terminal application (T043).

## Prerequisites

1. **py-spy installed**:
   ```bash
   pip install py-spy
   ```

2. **Server running**:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Baseline Profiling (T043)

### Quick Start

Run the automated baseline profiling script:

```bash
./scripts/profile-baseline.sh
```

This will:
1. **CPU Flamegraph** (60 seconds): Visualize where CPU time is spent
2. **Idle CPU Monitoring** (5 minutes): Track CPU usage over time
3. **Statistics Report**: Average, min, max CPU and memory usage

### Manual Profiling

If you need to profile manually:

#### 1. Find Server PID

```bash
ps aux | grep uvicorn | grep -v grep
```

#### 2. Run py-spy

```bash
# CPU flamegraph (60 seconds)
py-spy record \
    --pid <PID> \
    --duration 60 \
    --rate 100 \
    --output baseline_cpu.svg \
    --format flamegraph

# Top-style monitoring (real-time)
py-spy top --pid <PID>
```

#### 3. Monitor CPU with top/htop

```bash
# macOS
top -pid <PID>

# Linux
htop -p <PID>
```

## Understanding the Baseline

### Target Metrics (from T043)

- **Baseline CPU**: ~78.6% (current documented state)
- **Target after optimization**: <5% overhead
- **Optimization phases**:
  1. T044: WebSocket ping interval (60s) → ~5% reduction
  2. T045: Terminal output debouncing → TBD
  3. T046: Remove idle polling loops → TBD
  4. T047: Lazy-load xterm.js addons → Client-side only
  5. T048: Validate final CPU <5% overhead

### Reading the Flamegraph

The flamegraph (`baseline_cpu.svg`) shows:
- **X-axis**: Alphabetical ordering (NOT time)
- **Y-axis**: Stack depth
- **Width**: Proportion of CPU time
- **Color**: Random (for differentiation only)

**What to look for**:
- Wide bars at the top → CPU hotspots
- Common culprits:
  - WebSocket ping/pong loops
  - Polling loops in async tasks
  - Terminal output processing
  - Database queries

### Reading the CPU Log

The CPU log (`baseline_cpu_idle_*.log`) contains:
```
Timestamp, CPU %, Memory MB
2025-10-24 14:30:00, 78.2, 145.3
2025-10-24 14:30:05, 79.1, 145.5
...
```

**Analyze with**:
```bash
# Plot with gnuplot
gnuplot -e "set terminal png; set output 'cpu_plot.png'; plot 'baseline_cpu_idle_*.log' using 2 with lines title 'CPU %'"

# Calculate average with awk
awk -F, 'NR>3 {sum+=$2; count++} END {print "Average:", sum/count}' baseline_cpu_idle_*.log
```

## Profiling Best Practices

### 1. Consistent Environment

- Same hardware
- Same OS load
- Same terminal size
- Same session count
- Idle state (no user interaction)

### 2. Multiple Samples

Run profiling 3+ times and average results:

```bash
for i in {1..3}; do
    ./scripts/profile-baseline.sh
    sleep 60  # Cool-down period
done
```

### 3. Load Testing

For production profiling, simulate realistic load:

```bash
# Terminal 1: Start server
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Generate load
for i in {1..10}; do
    curl http://localhost:8000/api/terminal/sessions/new &
done

# Terminal 3: Profile
py-spy record --pid <PID> --duration 120 --output load_test.svg
```

## Optimization Workflow

### Phase 1: Establish Baseline (T043)

```bash
./scripts/profile-baseline.sh
```

**Output**:
- `baseline_cpu_<timestamp>.svg`
- `baseline_cpu_idle_<timestamp>.log`
- `baseline_summary_<timestamp>.txt`

### Phase 2: Optimize (T044-T047)

For each optimization:

1. **Before**: Profile with baseline script
2. **Implement**: Make code changes
3. **After**: Profile again
4. **Compare**: Calculate improvement

```bash
# Example: T044 (WebSocket ping interval)
./scripts/profile-baseline.sh  # Before
# Implement T044 changes
./scripts/profile-baseline.sh  # After
# Compare results
```

### Phase 3: Validate (T048)

```bash
# Final validation
./scripts/profile-baseline.sh

# Compare to original baseline
# Target: <5% overhead
```

## Common CPU Hotspots

Based on T043 research, typical hotspots include:

### 1. WebSocket Ping/Pong (T044)

**Before**:
```python
# websockets/terminal_handler.py
ping_interval=20  # Too frequent
```

**After**:
```python
ping_interval=60  # Optimized
```

**Expected savings**: ~5% CPU

### 2. Terminal Output Processing (T045)

**Before**: Immediate flush on every byte

**After**: Debounce output (10ms window)

**Expected savings**: TBD (depends on output volume)

### 3. Idle Polling Loops (T046)

**Look for**:
```python
while True:
    await asyncio.sleep(0.1)  # Tight loop!
    # Check something...
```

**Replace with**:
```python
# Event-driven approach
await event.wait()
```

### 4. Client-Side (T047)

Lazy-load xterm.js addons to reduce initial JS parse time.

## Output Files

All profile outputs are saved to `performance-profiles/`:

```
performance-profiles/
├── baseline_cpu_20251024_143000.svg        # Flamegraph
├── baseline_cpu_idle_20251024_143000.log   # Time series data
└── baseline_summary_20251024_143000.txt    # Summary report
```

## Troubleshooting

### "Permission denied" when profiling

macOS requires sudo for py-spy:

```bash
sudo py-spy record --pid <PID> ...
```

Or disable SIP (not recommended):
```bash
csrutil disable  # Requires reboot
```

### Server not found

Check if server is running:
```bash
ps aux | grep uvicorn
```

Start server if needed:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### High baseline CPU

If baseline CPU > 80%, investigate:
1. Background processes consuming CPU
2. Stuck loops in application code
3. Database query issues
4. WebSocket connection storms

## Next Steps

After completing T043 baseline profiling:

1. **Review** flamegraph and identify hotspots
2. **Proceed** with T044: Optimize WebSocket ping interval
3. **Iterate** through T045-T047 optimizations
4. **Validate** with T048: Final CPU target <5%

## Resources

- [py-spy documentation](https://github.com/benfred/py-spy)
- [Flamegraph visualization](https://www.brendangregg.com/flamegraphs.html)
- [Python profiling guide](https://docs.python.org/3/library/profile.html)
