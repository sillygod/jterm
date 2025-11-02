/**
 * Recording.js - Session recording playback controls
 *
 * Provides controls for recording terminal sessions and playing back recordings
 * with timeline navigation, speed control, and export functionality.
 */

class RecordingPlayer {
    constructor(containerId = 'recording-player') {
        this.containerId = containerId;
        this.recordingId = null;
        this.events = [];
        this.currentEventIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.playbackSpeed = 1.0;
        this.playbackTimer = null;
        this.startTime = null;
        this.currentTime = 0;
        this.duration = 0;

        // UI elements (will be set after DOM load)
        this.playButton = null;
        this.pauseButton = null;
        this.stopButton = null;
        this.timeline = null;
        this.timeCurrentDisplay = null;
        this.timeTotalDisplay = null;
        this.speedControl = null;

        // Scaling state (T042)
        this.terminalCols = null;
        this.terminalRows = null;
        this.currentScale = 1.0;
        this.scalingWrapper = null;
        this.scaleIndicator = null;
        this.resizeDebounceTimer = null;
        this.resizeDebounceMs = 200;

        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
    }

    setupUI() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.warn(`[RecordingPlayer] Container #${this.containerId} not found`);
            return;
        }

        // Get UI elements
        this.playButton = container.querySelector('.recording-play');
        this.pauseButton = container.querySelector('.recording-pause');
        this.stopButton = container.querySelector('.recording-stop');
        this.timeline = container.querySelector('.recording-timeline');
        this.timeCurrentDisplay = container.querySelector('.time-current');
        this.timeTotalDisplay = container.querySelector('.time-total');
        this.speedControl = container.querySelector('.recording-speed');

        console.log(`[RecordingPlayer] UI elements found:`, {
            playButton: !!this.playButton,
            pauseButton: !!this.pauseButton,
            stopButton: !!this.stopButton,
            timeline: !!this.timeline,
            timeCurrentDisplay: !!this.timeCurrentDisplay,
            timeTotalDisplay: !!this.timeTotalDisplay,
            speedControl: !!this.speedControl
        });

        // Setup event listeners
        if (this.playButton) {
            this.playButton.addEventListener('click', () => this.play());
        }
        if (this.pauseButton) {
            this.pauseButton.addEventListener('click', () => this.pause());
        }
        if (this.stopButton) {
            this.stopButton.addEventListener('click', () => this.stop());
        }
        if (this.timeline) {
            this.timeline.addEventListener('input', (e) => this.seek(parseFloat(e.target.value)));
            this.timeline.addEventListener('change', (e) => this.seek(parseFloat(e.target.value)));
        }
        if (this.speedControl) {
            this.speedControl.addEventListener('change', (e) => this.setSpeed(parseFloat(e.target.value)));
        }

        // Setup keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    async loadRecording(recordingId) {
        this.recordingId = recordingId;

        try {
            console.log(`[RecordingPlayer] Loading recording ${recordingId}...`);

            // Fetch recording events from API
            const eventsUrl = `/api/v1/recordings/${recordingId}/events?limit=10000`;
            console.log(`[RecordingPlayer] Fetching events from: ${eventsUrl}`);

            const response = await fetch(eventsUrl);
            if (!response.ok) {
                throw new Error(`Failed to load recording: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            this.events = data.events || [];

            console.log(`[RecordingPlayer] Loaded ${this.events.length} events`);
            if (this.events.length > 0) {
                console.log(`[RecordingPlayer] First event:`, this.events[0]);
                console.log(`[RecordingPlayer] Last event:`, this.events[this.events.length - 1]);
            }

            // Preprocess events: calculate cumulative time for each event
            let cumulativeTime = 0;
            for (const event of this.events) {
                // deltaTime from backend is milliseconds since previous event
                cumulativeTime += event.deltaTime || 0;
                event.cumulativeTime = cumulativeTime;
            }

            // Calculate duration from events
            if (this.events.length > 0) {
                const lastEvent = this.events[this.events.length - 1];

                // Use cumulative time which we just calculated
                this.duration = lastEvent.cumulativeTime || 0;

                console.log(`[RecordingPlayer] Duration calculated: ${this.duration}ms (${this.formatTime(this.duration)})`);
            } else {
                console.warn(`[RecordingPlayer] No events found, duration: ${this.duration}ms`);
            }

            // Fetch dimensions and setup scaling (T042)
            await this.fetchDimensions(recordingId);
            this.setupScaling(recordingId);
            this.applyScale();

            this.updateUI();
            console.log(`[RecordingPlayer] UI updated, current time: ${this.currentTime}, duration: ${this.duration}`);

            this.dispatchEvent('recording-loaded', { recordingId, eventCount: this.events.length });

            return true;
        } catch (error) {
            console.error('[RecordingPlayer] Failed to load recording:', error);
            this.dispatchEvent('recording-error', { error: error.message });
            return false;
        }
    }

    play() {
        if (this.events.length === 0) {
            console.warn('No recording loaded');
            return;
        }

        if (this.isPaused) {
            // Resume from pause
            this.isPaused = false;
            this.isPlaying = true;
            this.playNextEvent();
        } else {
            // Start from beginning or current position
            this.isPlaying = true;
            this.isPaused = false;
            this.startTime = Date.now() - this.currentTime;
            this.playNextEvent();
        }

        this.updateUI();
        this.dispatchEvent('recording-play');
    }

    pause() {
        if (!this.isPlaying) return;

        this.isPaused = true;
        this.isPlaying = false;

        if (this.playbackTimer) {
            clearTimeout(this.playbackTimer);
            this.playbackTimer = null;
        }

        this.updateUI();
        this.dispatchEvent('recording-pause');
    }

    stop() {
        this.isPlaying = false;
        this.isPaused = false;
        this.currentEventIndex = 0;
        this.currentTime = 0;

        if (this.playbackTimer) {
            clearTimeout(this.playbackTimer);
            this.playbackTimer = null;
        }

        this.updateUI();
        this.dispatchEvent('recording-stop');
    }

    seek(position) {
        // Position is between 0 and 1
        const targetTime = position * this.duration;

        // Find the event closest to target time using cumulative time
        let targetIndex = 0;
        for (let i = 0; i < this.events.length; i++) {
            const event = this.events[i];
            const eventTime = event.cumulativeTime || 0;

            if (eventTime <= targetTime) {
                targetIndex = i;
            } else {
                break;
            }
        }

        this.currentEventIndex = targetIndex;
        this.currentTime = targetTime;
        this.startTime = Date.now() - this.currentTime;

        // Replay events up to this point if playing
        if (this.isPlaying) {
            this.replayToPosition(targetIndex);
        }

        this.updateUI();
        this.dispatchEvent('recording-seek', { position, time: targetTime });
    }

    setSpeed(speed) {
        this.playbackSpeed = speed;
        this.updateUI();
        this.dispatchEvent('recording-speed-change', { speed });
    }

    playNextEvent() {
        if (!this.isPlaying || this.isPaused) return;
        if (this.currentEventIndex >= this.events.length) {
            this.stop();
            this.dispatchEvent('recording-end');
            return;
        }

        const event = this.events[this.currentEventIndex];
        // Use cumulative time which was calculated during loadRecording
        const eventTime = event.cumulativeTime || 0;

        // Calculate delay until next event (adjusted for playback speed)
        const currentPlayTime = Date.now() - this.startTime;
        let delay = (eventTime - currentPlayTime) / this.playbackSpeed;

        if (delay < 0) delay = 0;

        this.playbackTimer = setTimeout(() => {
            // Write event data to terminal
            this.writeEvent(event);

            this.currentEventIndex++;
            this.currentTime = eventTime;
            this.updateUI();

            // Schedule next event
            this.playNextEvent();
        }, delay);
    }

    writeEvent(event) {
        // Dispatch event for terminal to handle
        this.dispatchEvent('recording-event', {
            type: event.type,
            data: event.data,
            timestamp: event.timestamp
        });

        // If there's a global terminal instance, write to it
        if (window.webTerminal && event.type === 'output') {
            window.webTerminal.terminal.write(event.data);
        }
    }

    replayToPosition(targetIndex) {
        // Clear terminal and replay events up to target index
        if (window.webTerminal) {
            window.webTerminal.terminal.clear();
        }

        for (let i = 0; i <= targetIndex; i++) {
            const event = this.events[i];
            if (event.type === 'output') {
                this.writeEvent(event);
            }
        }
    }

    updateUI() {
        // Update play/pause button states
        if (this.playButton && this.pauseButton) {
            if (this.isPlaying) {
                this.playButton.style.display = 'none';
                this.pauseButton.style.display = 'inline-block';
            } else {
                this.playButton.style.display = 'inline-block';
                this.pauseButton.style.display = 'none';
            }
        }

        // Update timeline
        if (this.timeline && this.duration > 0) {
            const position = this.currentTime / this.duration;
            this.timeline.value = position;
        }

        // Update time displays (separate current and total elements)
        if (this.timeCurrentDisplay) {
            const current = this.formatTime(this.currentTime);
            this.timeCurrentDisplay.textContent = current;
        }
        if (this.timeTotalDisplay) {
            const total = this.formatTime(this.duration);
            this.timeTotalDisplay.textContent = total;
        }

        // Update speed display
        if (this.speedControl) {
            this.speedControl.value = this.playbackSpeed;
        }
    }

    formatTime(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        const s = seconds % 60;
        const m = minutes % 60;

        if (hours > 0) {
            return `${hours}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        } else {
            return `${m}:${s.toString().padStart(2, '0')}`;
        }
    }

    handleKeyboard(e) {
        // Only handle if recording player is active
        if (!this.recordingId) return;

        // Don't interfere with input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.key) {
            case ' ':
                e.preventDefault();
                if (this.isPlaying) {
                    this.pause();
                } else {
                    this.play();
                }
                break;
            case 'ArrowLeft':
                e.preventDefault();
                this.skip(-5000); // Skip back 5 seconds
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.skip(5000); // Skip forward 5 seconds
                break;
            case 'Home':
                e.preventDefault();
                this.seek(0);
                break;
            case 'End':
                e.preventDefault();
                this.seek(1);
                break;
        }
    }

    skip(milliseconds) {
        const newTime = Math.max(0, Math.min(this.duration, this.currentTime + milliseconds));
        const position = newTime / this.duration;
        this.seek(position);
    }

    /**
     * Fetch recording dimensions from API (T042)
     */
    async fetchDimensions(recordingId) {
        try {
            const response = await fetch(`/api/recordings/${recordingId}/dimensions`);
            if (!response.ok) {
                console.warn('Failed to fetch dimensions, using defaults');
                this.terminalCols = 80;
                this.terminalRows = 24;
                return;
            }

            const data = await response.json();
            this.terminalCols = data.cols || 80;
            this.terminalRows = data.rows || 24;

            console.log('Recording dimensions:', {
                cols: this.terminalCols,
                rows: this.terminalRows
            });
        } catch (error) {
            console.warn('Error fetching dimensions:', error);
            this.terminalCols = 80;
            this.terminalRows = 24;
        }
    }

    /**
     * Setup scaling elements and resize listener (T042)
     */
    setupScaling(recordingId) {
        // Cache scaling wrapper and indicator elements
        this.scalingWrapper = document.getElementById(`playback-scaling-wrapper-${recordingId}`);
        this.scaleIndicator = document.getElementById(`scale-value-${recordingId}`);

        if (!this.scalingWrapper) {
            console.warn('Scaling wrapper not found, scaling disabled');
            return;
        }

        // Read dimensions from data attributes if available
        if (this.scalingWrapper.dataset.terminalCols) {
            this.terminalCols = parseInt(this.scalingWrapper.dataset.terminalCols);
        }
        if (this.scalingWrapper.dataset.terminalRows) {
            this.terminalRows = parseInt(this.scalingWrapper.dataset.terminalRows);
        }

        // Setup resize listener with debouncing (200ms as per T042)
        const debouncedResize = () => {
            if (this.resizeDebounceTimer) {
                clearTimeout(this.resizeDebounceTimer);
            }

            this.resizeDebounceTimer = setTimeout(() => {
                const startTime = performance.now();
                this.applyScale();
                const endTime = performance.now();
                const latency = endTime - startTime;

                console.log(`Resize latency: ${latency.toFixed(2)}ms`);

                // Validate < 200ms requirement from T014
                if (latency > 200) {
                    console.warn(`Resize latency exceeded 200ms: ${latency.toFixed(2)}ms`);
                }
            }, this.resizeDebounceMs);
        };

        // Add resize listener
        window.addEventListener('resize', debouncedResize);

        // Store reference for cleanup
        this.resizeListener = debouncedResize;
    }

    /**
     * Calculate and apply scale transform (T042)
     */
    applyScale() {
        if (!this.scalingWrapper || !this.terminalCols) {
            return;
        }

        // Get viewport dimensions
        const viewer = this.scalingWrapper.closest('.playback-viewer');
        if (!viewer) {
            console.warn('Playback viewer not found');
            return;
        }

        const viewportWidth = viewer.clientWidth;
        const viewportHeight = viewer.clientHeight;

        // Calculate terminal dimensions (9px char width, 17px char height)
        const charWidth = 9;
        const charHeight = 17;
        const terminalWidth = this.terminalCols * charWidth;
        const terminalHeight = this.terminalRows * charHeight;

        // Calculate scale: min(1.0, viewportWidth / terminalWidth)
        const scaleX = viewportWidth / terminalWidth;
        const scaleY = viewportHeight / terminalHeight;
        const scale = Math.min(1.0, scaleX, scaleY);

        // Apply transform
        this.currentScale = scale;
        this.scalingWrapper.style.transform = `scale(${scale})`;

        // Update scale indicator
        if (this.scaleIndicator) {
            this.scaleIndicator.textContent = `${Math.round(scale * 100)}%`;
        }

        console.log('Scale applied:', {
            viewportWidth,
            viewportHeight,
            terminalWidth,
            terminalHeight,
            scale: `${Math.round(scale * 100)}%`
        });
    }

    /**
     * Cleanup scaling (call when destroying player)
     */
    cleanupScaling() {
        if (this.resizeListener) {
            window.removeEventListener('resize', this.resizeListener);
            this.resizeListener = null;
        }

        if (this.resizeDebounceTimer) {
            clearTimeout(this.resizeDebounceTimer);
            this.resizeDebounceTimer = null;
        }
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }

    async exportRecording(format = 'json') {
        if (!this.recordingId) {
            console.warn('No recording loaded');
            return;
        }

        try {
            const response = await fetch(`/api/v1/recordings/${this.recordingId}/export`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ format })
            });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Download the file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `recording_${this.recordingId}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.dispatchEvent('recording-exported', { format });
        } catch (error) {
            console.error('Export failed:', error);
            this.dispatchEvent('recording-error', { error: error.message });
        }
    }
}

// Recording Controller for active sessions
class RecordingController {
    constructor() {
        this.isRecording = false;
        this.recordingId = null;
        this.sessionId = null;
        this.startButton = null;
        this.stopButton = null;
        this.statusIndicator = null;

        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUI());
        } else {
            this.setupUI();
        }
    }

    setupUI() {
        this.startButton = document.querySelector('.recording-start');
        this.stopButton = document.querySelector('.recording-stop-record');
        this.statusIndicator = document.querySelector('.recording-status');

        // Remove any existing event listeners by cloning and replacing elements
        if (this.startButton) {
            const newStartButton = this.startButton.cloneNode(true);
            this.startButton.parentNode.replaceChild(newStartButton, this.startButton);
            this.startButton = newStartButton;
            this.startButton.addEventListener('click', () => this.startRecording());
        }
        if (this.stopButton) {
            const newStopButton = this.stopButton.cloneNode(true);
            this.stopButton.parentNode.replaceChild(newStopButton, this.stopButton);
            this.stopButton = newStopButton;
            this.stopButton.addEventListener('click', () => this.stopRecording());
        }

        this.updateUI();
    }

    async startRecording(sessionId = null) {
        this.sessionId = sessionId || this.getCurrentSessionId();

        if (!this.sessionId) {
            console.error('No session ID available');
            return false;
        }

        try {
            // Start recording via API - backend generates the recording ID
            const response = await fetch('/api/v1/recordings/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    sessionId: this.sessionId,
                    metadata: {
                        startedAt: new Date().toISOString()
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to start recording: ${response.statusText}`);
            }

            // Get the recording ID from the response
            const data = await response.json();
            this.recordingId = data.recordingId;

            this.isRecording = true;
            this.updateUI();
            this.dispatchEvent('recording-started', { recordingId: this.recordingId });

            return true;
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.dispatchEvent('recording-error', { error: error.message });
            return false;
        }
    }

    async stopRecording() {
        if (!this.isRecording || !this.recordingId) {
            return false;
        }

        try {
            const response = await fetch(`/api/v1/recordings/${this.recordingId}/stop`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`Failed to stop recording: ${response.statusText}`);
            }

            const data = await response.json();

            this.isRecording = false;
            this.updateUI();
            this.dispatchEvent('recording-stopped', {
                recordingId: this.recordingId,
                duration: data.duration,
                eventCount: data.eventCount
            });

            const stoppedRecordingId = this.recordingId;
            this.recordingId = null;

            return stoppedRecordingId;
        } catch (error) {
            console.error('Failed to stop recording:', error);
            this.dispatchEvent('recording-error', { error: error.message });
            return false;
        }
    }

    updateUI() {
        if (this.startButton && this.stopButton) {
            if (this.isRecording) {
                this.startButton.style.display = 'none';
                this.stopButton.style.display = 'inline-block';
            } else {
                this.startButton.style.display = 'inline-block';
                this.stopButton.style.display = 'none';
            }
        }

        if (this.statusIndicator) {
            if (this.isRecording) {
                this.statusIndicator.textContent = 'Recording';
                this.statusIndicator.classList.add('recording-active');
            } else {
                this.statusIndicator.textContent = '';
                this.statusIndicator.classList.remove('recording-active');
            }
        }
    }

    getCurrentSessionId() {
        // Try to get session ID from global terminal instance
        if (window.webTerminal && window.webTerminal.sessionId) {
            return window.webTerminal.sessionId;
        }

        // Try to get from URL params
        const params = new URLSearchParams(window.location.search);
        return params.get('sessionId');
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
}

// Initialize global instances (singleton pattern)
let recordingPlayer = null;
let recordingController = null;

// Global recording player manager for multiple playback instances
if (!window.recordingPlayer) {
    window.recordingPlayer = {
        players: new Map(),

        /**
         * Initialize a recording player instance (called from template script)
         * @param {string} recordingId - The recording ID
         * @param {Object} options - Configuration options
         */
        async init(recordingId, options = {}) {
            console.log('[RecordingPlayer.init] Starting initialization for:', recordingId, 'with options:', options);

            const { terminalCols, terminalRows, duration, autoScale = true } = options;

            // Create player instance for this recording
            const player = new RecordingPlayer(`recording-playback-${recordingId}`);
            player.recordingId = recordingId;
            player.terminalCols = terminalCols;
            player.terminalRows = terminalRows;

            // Store preliminary duration from template (will be recalculated after loading events)
            if (duration) {
                player.duration = this.parseDuration(duration);
                console.log('[RecordingPlayer.init] Parsed duration from template:', player.duration, 'ms');
            }

            this.players.set(recordingId, player);

            // Load the recording events (this calculates cumulative time and accurate duration)
            console.log('[RecordingPlayer.init] Calling loadRecording...');
            const success = await player.loadRecording(recordingId);

            if (success) {
                console.log('[RecordingPlayer.init] Successfully initialized and loaded:', recordingId);
            } else {
                console.error('[RecordingPlayer.init] Failed to load recording:', recordingId);
            }

            return player;
        },

        /**
         * Get player instance by recording ID
         */
        getPlayer(recordingId) {
            return this.players.get(recordingId);
        },

        /**
         * Toggle play/pause for a recording
         */
        togglePlayPause(recordingId) {
            const player = this.players.get(recordingId);
            if (!player) return;

            if (player.isPlaying) {
                player.pause();
            } else {
                player.play();
            }
        },

        /**
         * Stop playback
         */
        stop(recordingId) {
            const player = this.players.get(recordingId);
            if (player) {
                player.stop();
            }
        },

        /**
         * Seek to position (0-100)
         */
        seek(recordingId, value) {
            const player = this.players.get(recordingId);
            if (player) {
                player.seek(parseFloat(value) / 100);
            }
        },

        /**
         * Seek backward by seconds
         */
        seekBackward(recordingId, seconds) {
            const player = this.players.get(recordingId);
            if (player) {
                player.skip(-seconds * 1000);
            }
        },

        /**
         * Seek forward by seconds
         */
        seekForward(recordingId, seconds) {
            const player = this.players.get(recordingId);
            if (player) {
                player.skip(seconds * 1000);
            }
        },

        /**
         * Set playback speed
         */
        setSpeed(recordingId, speed) {
            const player = this.players.get(recordingId);
            if (player) {
                player.setSpeed(parseFloat(speed));
            }
        },

        /**
         * Retry loading a recording (called from error state)
         */
        async retry(recordingId) {
            const player = this.players.get(recordingId);
            if (player) {
                await player.loadRecording(recordingId);
            }
        },

        /**
         * Parse duration string (MM:SS or HH:MM:SS) to milliseconds
         */
        parseDuration(durationStr) {
            const parts = durationStr.split(':').map(Number);
            let milliseconds = 0;

            if (parts.length === 2) {
                // MM:SS
                milliseconds = (parts[0] * 60 + parts[1]) * 1000;
            } else if (parts.length === 3) {
                // HH:MM:SS
                milliseconds = (parts[0] * 3600 + parts[1] * 60 + parts[2]) * 1000;
            }

            return milliseconds;
        }
    };
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize recording controller (singleton)
    if (!window.recordingController) {
        recordingController = new RecordingController();
        window.recordingController = recordingController;
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { RecordingPlayer, RecordingController };
}
