/**
 * Performance Monitor - Client-side performance metrics collection and display
 * Collects client metrics (FPS, memory), receives server metrics via WebSocket,
 * and updates the performance widget UI.
 */

class PerformanceMonitor {
    constructor() {
        // Configuration
        this.enabled = false;
        this.refreshInterval = 5000; // Default 5 seconds (1000-60000ms range)
        this.sessionId = null;

        // State
        this.lastServerUpdate = null;
        this.metricsHistory = [];
        this.maxHistoryLength = 60; // Keep 60 data points for sparklines

        // FPS tracking
        this.fps = 0;
        this.frameCount = 0;
        this.lastFpsCheck = performance.now();
        this.fpsAnimationId = null;

        // Timers
        this.clientMetricsTimer = null;
        this.serverRefreshTimer = null;

        // DOM references (cached)
        this.widget = null;
        this.elements = {};

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupAfterLoad());
        } else {
            this.setupAfterLoad();
        }
    }

    setupAfterLoad() {
        // Cache DOM elements
        this.cacheElements();

        // Load user preferences
        this.loadPreferences();

        // Setup event listeners
        this.setupEventListeners();

        // Initialize if enabled
        if (this.enabled) {
            this.start();
        }

        console.log('PerformanceMonitor initialized', {
            enabled: this.enabled,
            refreshInterval: this.refreshInterval
        });
    }

    cacheElements() {
        this.widget = document.getElementById('performance-widget');

        // Server metrics
        this.elements.cpu = document.getElementById('metric-cpu');
        this.elements.cpuBar = document.getElementById('metric-cpu-bar');
        this.elements.memory = document.getElementById('metric-memory');
        this.elements.memoryBar = document.getElementById('metric-memory-bar');
        this.elements.websockets = document.getElementById('metric-websockets');
        this.elements.updates = document.getElementById('metric-updates');

        // Client metrics
        this.elements.fps = document.getElementById('metric-fps');
        this.elements.clientMemory = document.getElementById('metric-client-memory');

        // Controls
        this.elements.lastUpdate = document.getElementById('last-update');
        this.elements.status = document.getElementById('performance-status');
        this.elements.historyChart = document.getElementById('history-chart');
    }

    loadPreferences() {
        // Load from localStorage
        const showMetrics = localStorage.getItem('show_performance_metrics');
        const interval = localStorage.getItem('performance_metric_refresh_interval');

        this.enabled = showMetrics === 'true';
        this.refreshInterval = interval ? parseInt(interval) : 5000;

        // Apply to widget
        if (this.widget) {
            this.widget.style.display = this.enabled ? 'block' : 'none';
            this.widget.setAttribute('data-enabled', this.enabled.toString());
        }
    }

    setupEventListeners() {
        // Listen for WebSocket messages with performance data
        document.addEventListener('htmx:wsAfterMessage', (e) => {
            const message = e.detail.message;
            if (message.type === 'performance_update') {
                this.handleServerMetrics(message.data);
            }
        });

        // Listen for preference changes
        document.addEventListener('performance-preferences-updated', (e) => {
            this.updatePreferences(e.detail);
        });

        // Window visibility change (pause when hidden)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pause();
            } else if (this.enabled) {
                this.resume();
            }
        });
    }

    /**
     * Start performance monitoring
     */
    start() {
        if (!this.enabled) return;

        console.log('Starting performance monitoring');

        // Show widget
        if (this.widget) {
            this.widget.style.display = 'block';
        }

        // Start FPS tracking
        this.startFpsTracking();

        // Start client metrics collection
        this.startClientMetrics();

        // Start server metrics refresh
        this.startServerRefresh();
    }

    /**
     * Stop performance monitoring
     */
    stop() {
        console.log('Stopping performance monitoring');

        // Stop timers
        this.stopFpsTracking();
        this.stopClientMetrics();
        this.stopServerRefresh();

        // Hide widget
        if (this.widget) {
            this.widget.style.display = 'none';
        }
    }

    /**
     * Pause monitoring (when tab hidden)
     */
    pause() {
        this.stopFpsTracking();
        this.stopClientMetrics();
        this.stopServerRefresh();
    }

    /**
     * Resume monitoring (when tab visible again)
     */
    resume() {
        if (this.enabled) {
            this.startFpsTracking();
            this.startClientMetrics();
            this.startServerRefresh();
        }
    }

    /**
     * Update user preferences
     */
    updatePreferences(preferences) {
        const { show_performance_metrics, performance_metric_refresh_interval } = preferences;

        const wasEnabled = this.enabled;

        if (show_performance_metrics !== undefined) {
            this.enabled = show_performance_metrics;
            localStorage.setItem('show_performance_metrics', show_performance_metrics.toString());
        }

        if (performance_metric_refresh_interval !== undefined) {
            this.refreshInterval = performance_metric_refresh_interval;
            localStorage.setItem('performance_metric_refresh_interval', performance_metric_refresh_interval.toString());

            // Restart client metrics with new interval
            if (this.enabled) {
                this.stopClientMetrics();
                this.startClientMetrics();
            }
        }

        // Toggle monitoring based on enabled state
        if (this.enabled && !wasEnabled) {
            this.start();
        } else if (!this.enabled && wasEnabled) {
            this.stop();
        }
    }

    /**
     * Set refresh interval dynamically
     * @param {number} intervalMs - New refresh interval in milliseconds
     */
    setInterval(intervalMs) {
        if (intervalMs < 1000 || intervalMs > 60000) {
            console.warn('Invalid refresh interval. Must be between 1000ms and 60000ms');
            return;
        }

        this.refreshInterval = intervalMs;
        localStorage.setItem('metrics_refresh_interval', intervalMs.toString());

        // Restart both client metrics and server refresh with new interval if currently running
        if (this.enabled) {
            if (this.clientMetricsTimer) {
                this.stopClientMetrics();
                this.startClientMetrics();
            }
            if (this.serverRefreshTimer) {
                this.stopServerRefresh();
                this.startServerRefresh();
            }
        }

        console.log('Performance metrics refresh interval updated:', intervalMs);
    }

    /**
     * Start FPS tracking
     */
    startFpsTracking() {
        if (this.fpsAnimationId) return; // Already running

        const measureFps = (timestamp) => {
            this.frameCount++;

            const elapsed = timestamp - this.lastFpsCheck;
            if (elapsed >= 1000) { // Update every second
                this.fps = Math.round((this.frameCount * 1000) / elapsed);
                this.frameCount = 0;
                this.lastFpsCheck = timestamp;

                // Update UI
                this.updateClientFps(this.fps);
            }

            this.fpsAnimationId = requestAnimationFrame(measureFps);
        };

        this.fpsAnimationId = requestAnimationFrame(measureFps);
    }

    /**
     * Stop FPS tracking
     */
    stopFpsTracking() {
        if (this.fpsAnimationId) {
            cancelAnimationFrame(this.fpsAnimationId);
            this.fpsAnimationId = null;
        }
    }

    /**
     * Start client metrics collection and submission
     */
    startClientMetrics() {
        if (this.clientMetricsTimer) return; // Already running

        const collectAndSend = async () => {
            const metrics = this.collectClientMetrics();
            await this.submitClientMetrics(metrics);
        };

        // Collect immediately, then on interval
        collectAndSend();
        this.clientMetricsTimer = setInterval(collectAndSend, this.refreshInterval);
    }

    /**
     * Stop client metrics collection
     */
    stopClientMetrics() {
        if (this.clientMetricsTimer) {
            clearInterval(this.clientMetricsTimer);
            this.clientMetricsTimer = null;
        }
    }

    /**
     * Start server metrics refresh
     */
    startServerRefresh() {
        if (this.serverRefreshTimer) return; // Already running

        // Refresh immediately, then on interval
        this.refreshNow();
        this.serverRefreshTimer = setInterval(() => {
            this.refreshNow();
        }, this.refreshInterval);
    }

    /**
     * Stop server metrics refresh
     */
    stopServerRefresh() {
        if (this.serverRefreshTimer) {
            clearInterval(this.serverRefreshTimer);
            this.serverRefreshTimer = null;
        }
    }

    /**
     * Collect client-side metrics
     */
    collectClientMetrics() {
        const metrics = {
            client_fps: this.fps,
            client_memory_mb: null
        };

        // Try to get memory usage (Chrome/Edge only)
        if (performance.memory) {
            const memoryMB = performance.memory.usedJSHeapSize / (1024 * 1024);
            metrics.client_memory_mb = Math.round(memoryMB * 10) / 10; // Round to 1 decimal
        }

        return metrics;
    }

    /**
     * Submit client metrics to server
     */
    async submitClientMetrics(metrics) {
        if (!this.sessionId) {
            // Try to get session ID from terminal
            if (window.webTerminal && window.webTerminal.sessionId) {
                this.sessionId = window.webTerminal.sessionId;
            } else {
                // Use a default/fallback session ID
                this.sessionId = '00000000-0000-0000-0000-000000000001';
            }
        }

        // Update client metrics in UI immediately
        if (metrics.client_memory_mb !== null) {
            this.updateClientMemory(metrics.client_memory_mb);
        }

        try {
            const response = await fetch('/api/performance/snapshot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    client_fps: metrics.client_fps,
                    client_memory_mb: metrics.client_memory_mb
                })
            });

            if (!response.ok) {
                console.warn('Failed to submit client metrics:', response.status);
            }
        } catch (error) {
            console.error('Error submitting client metrics:', error);
        }
    }

    /**
     * Handle server metrics received via WebSocket
     */
    handleServerMetrics(data) {
        this.lastServerUpdate = new Date();

        // Update UI with server metrics
        this.updateServerMetrics(data);

        // Add to history for charts
        this.addToHistory(data);

        // Update last update time
        this.updateLastUpdateTime();
    }

    /**
     * Update server metrics in UI
     */
    updateServerMetrics(data) {
        const {
            cpu_percent,
            memory_mb,
            active_websockets,
            terminal_updates_per_sec
        } = data;

        // CPU
        if (this.elements.cpu && cpu_percent !== undefined) {
            this.elements.cpu.textContent = cpu_percent.toFixed(1);

            if (this.elements.cpuBar) {
                this.elements.cpuBar.style.width = `${Math.min(cpu_percent, 100)}%`;

                // Update threshold class
                if (cpu_percent >= 80) {
                    this.elements.cpuBar.setAttribute('data-threshold', 'danger');
                } else if (cpu_percent >= 50) {
                    this.elements.cpuBar.setAttribute('data-threshold', 'warning');
                } else {
                    this.elements.cpuBar.removeAttribute('data-threshold');
                }
            }
        }

        // Memory
        if (this.elements.memory && memory_mb !== undefined) {
            this.elements.memory.textContent = memory_mb.toFixed(1);

            if (this.elements.memoryBar) {
                // Assume max 1GB for visualization (adjust as needed)
                const maxMemory = 1024;
                const percentage = Math.min((memory_mb / maxMemory) * 100, 100);
                this.elements.memoryBar.style.width = `${percentage}%`;
            }
        }

        // WebSockets
        if (this.elements.websockets && active_websockets !== undefined) {
            this.elements.websockets.textContent = active_websockets;
        }

        // Updates/sec
        if (this.elements.updates && terminal_updates_per_sec !== undefined) {
            this.elements.updates.textContent = terminal_updates_per_sec.toFixed(1);
        }

        // Update status indicator
        this.updateStatusIndicator(cpu_percent);
    }

    /**
     * Update client FPS in UI
     */
    updateClientFps(fps) {
        if (this.elements.fps) {
            this.elements.fps.textContent = fps;
        }
    }

    /**
     * Update client memory in UI
     */
    updateClientMemory(memoryMB) {
        if (this.elements.clientMemory) {
            this.elements.clientMemory.textContent = memoryMB !== null
                ? memoryMB.toFixed(1)
                : 'N/A';
        }
    }

    /**
     * Update last update time
     */
    updateLastUpdateTime() {
        if (!this.elements.lastUpdate) return;

        if (!this.lastServerUpdate) {
            this.elements.lastUpdate.textContent = 'Never';
            return;
        }

        const now = new Date();
        const diff = Math.floor((now - this.lastServerUpdate) / 1000); // seconds

        let text;
        if (diff < 10) {
            text = 'Just now';
        } else if (diff < 60) {
            text = `${diff}s ago`;
        } else if (diff < 3600) {
            text = `${Math.floor(diff / 60)}m ago`;
        } else {
            text = `${Math.floor(diff / 3600)}h ago`;
        }

        this.elements.lastUpdate.textContent = text;
    }

    /**
     * Update status indicator based on CPU
     */
    updateStatusIndicator(cpuPercent) {
        if (!this.elements.status) return;

        const dot = this.elements.status.querySelector('.status-dot');
        const text = this.elements.status.querySelector('.status-text');

        if (!dot || !text) return;

        if (cpuPercent >= 80) {
            dot.className = 'status-dot status-error';
            text.textContent = 'High CPU';
        } else if (cpuPercent >= 50) {
            dot.className = 'status-dot status-warning';
            text.textContent = 'Warning';
        } else {
            dot.className = 'status-dot status-ok';
            text.textContent = 'Monitoring';
        }
    }

    /**
     * Add metrics to history for charts
     */
    addToHistory(data) {
        this.metricsHistory.push({
            timestamp: Date.now(),
            cpu: data.cpu_percent,
            memory: data.memory_mb,
            websockets: data.active_websockets,
            updates: data.terminal_updates_per_sec,
            fps: this.fps,
            clientMemory: this.collectClientMetrics().client_memory_mb
        });

        // Keep only recent history
        if (this.metricsHistory.length > this.maxHistoryLength) {
            this.metricsHistory.shift();
        }
    }

    /**
     * Refresh metrics now (manual refresh button)
     */
    async refreshNow() {
        try {
            const response = await fetch('/api/performance/current');

            if (!response.ok) {
                throw new Error('Failed to fetch current metrics');
            }

            const data = await response.json();
            this.handleServerMetrics(data);

        } catch (error) {
            console.error('Error refreshing metrics:', error);
            this.showError('Failed to refresh metrics');
        }
    }

    /**
     * Load historical data for charts
     */
    async loadHistory(minutes = 15) {
        if (!this.elements.historyChart) return;

        try {
            const response = await fetch(`/api/performance/history?minutes=${minutes}`);

            if (!response.ok) {
                throw new Error('Failed to fetch history');
            }

            const data = await response.json();
            this.renderHistoryChart(data.snapshots);

        } catch (error) {
            console.error('Error loading history:', error);
            this.elements.historyChart.innerHTML = `
                <div class="chart-placeholder">
                    <p>Failed to load history</p>
                </div>
            `;
        }
    }

    /**
     * Render history chart (simple sparkline)
     */
    renderHistoryChart(snapshots) {
        if (!this.elements.historyChart || !snapshots || snapshots.length === 0) {
            return;
        }

        // Simple text-based sparkline for now
        // In production, you might use Chart.js or similar
        const cpuValues = snapshots.map(s => s.cpu_percent);
        const maxCpu = Math.max(...cpuValues);
        const minCpu = Math.min(...cpuValues);

        const sparkline = this.generateSparkline(cpuValues, maxCpu, minCpu);

        this.elements.historyChart.innerHTML = `
            <div class="chart-metrics">
                <div class="chart-row">
                    <span class="chart-label">CPU %</span>
                    <span class="chart-value">${cpuValues[cpuValues.length - 1].toFixed(1)}%</span>
                    <span class="chart-range">${minCpu.toFixed(1)}% - ${maxCpu.toFixed(1)}%</span>
                </div>
                <div class="chart-sparkline" style="font-family: monospace; font-size: 0.75rem;">
                    ${sparkline}
                </div>
            </div>
        `;
    }

    /**
     * Generate simple ASCII sparkline
     */
    generateSparkline(values, max, min) {
        const bars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
        const range = max - min || 1;

        return values.map(val => {
            const normalized = (val - min) / range;
            const index = Math.floor(normalized * (bars.length - 1));
            return bars[Math.max(0, Math.min(index, bars.length - 1))];
        }).join('');
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('PerformanceMonitor error:', message);

        if (this.elements.status) {
            const text = this.elements.status.querySelector('.status-text');
            if (text) {
                text.textContent = 'Error';
            }
        }
    }
}

// Initialize global instance
window.performanceMonitor = new PerformanceMonitor();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceMonitor;
}
