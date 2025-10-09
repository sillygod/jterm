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
        this.timeDisplay = null;
        this.speedControl = null;

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
            console.warn(`Recording player container #${this.containerId} not found`);
            return;
        }

        // Get UI elements
        this.playButton = container.querySelector('.recording-play');
        this.pauseButton = container.querySelector('.recording-pause');
        this.stopButton = container.querySelector('.recording-stop');
        this.timeline = container.querySelector('.recording-timeline');
        this.timeDisplay = container.querySelector('.recording-time');
        this.speedControl = container.querySelector('.recording-speed');

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
            // Fetch recording events from API
            const response = await fetch(`/api/v1/recordings/${recordingId}/events?limit=10000`);
            if (!response.ok) {
                throw new Error(`Failed to load recording: ${response.statusText}`);
            }

            const data = await response.json();
            this.events = data.events;

            // Calculate duration from events
            if (this.events.length > 0) {
                const lastEvent = this.events[this.events.length - 1];
                this.duration = new Date(lastEvent.timestamp).getTime() -
                               new Date(this.events[0].timestamp).getTime();
            }

            this.updateUI();
            this.dispatchEvent('recording-loaded', { recordingId, eventCount: this.events.length });

            return true;
        } catch (error) {
            console.error('Failed to load recording:', error);
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

        // Find the event closest to target time
        let targetIndex = 0;
        for (let i = 0; i < this.events.length; i++) {
            const eventTime = new Date(this.events[i].timestamp).getTime() -
                            new Date(this.events[0].timestamp).getTime();
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
        const eventTime = new Date(event.timestamp).getTime() -
                         new Date(this.events[0].timestamp).getTime();

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

        // Update time display
        if (this.timeDisplay) {
            const current = this.formatTime(this.currentTime);
            const total = this.formatTime(this.duration);
            this.timeDisplay.textContent = `${current} / ${total}`;
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

document.addEventListener('DOMContentLoaded', () => {
    // Initialize recording player if player container exists (singleton)
    if (document.getElementById('recording-player') && !window.recordingPlayer) {
        recordingPlayer = new RecordingPlayer('recording-player');
        window.recordingPlayer = recordingPlayer;
    }

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
