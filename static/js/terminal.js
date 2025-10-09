/**
 * Terminal.js - xterm.js integration for Web Terminal
 */

class WebTerminal {
    constructor(containerId = 'xterm-container') {
        this.containerId = containerId;
        this.terminal = null;
        this.websocket = null;
        this.fitAddon = null;
        this.sessionId = null;
        this.isConnected = false;

        this.init();
    }

    init() {
        // Initialize xterm.js terminal
        this.terminal = new Terminal({
            theme: {
                background: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-bg').trim() || '#000000',
                foreground: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-fg').trim() || '#ffffff',
                cursor: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-cursor').trim() || '#ffffff',
                selection: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-selection').trim() || 'rgba(255, 255, 255, 0.3)',
            },
            fontFamily: '"Courier New", Courier, monospace',
            fontSize: 14,
            lineHeight: 1.0,
            letterSpacing: 0,
            cursorBlink: true,
            allowTransparency: false,
            rightClickSelectsWord: true,
            scrollback: 10000,
            convertEol: false,
            allowProposedApi: true,
            drawBoldTextInBrightColors: true,
            fontWeight: 'normal',
            fontWeightBold: 'bold',
        });

        // Add addons
        this.fitAddon = new FitAddon.FitAddon();
        this.terminal.loadAddon(this.fitAddon);
        this.terminal.loadAddon(new WebLinksAddon.WebLinksAddon());
        this.terminal.loadAddon(new SearchAddon.SearchAddon());

        // Add Unicode11 addon for proper box-drawing character support
        const unicode11Addon = new Unicode11Addon.Unicode11Addon();
        this.terminal.loadAddon(unicode11Addon);
        this.terminal.unicode.activeVersion = '11';

        // Get container and open terminal
        const container = document.getElementById(this.containerId);
        if (container) {
            this.terminal.open(container);
            this.fitAddon.fit();
        }

        this.setupEventListeners();
        this.connectWebSocket();
    }

    setupEventListeners() {
        // Terminal data handler
        this.terminal.onData((data) => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'input',
                    data: data,
                    sessionId: this.sessionId,
                    timestamp: new Date().toISOString()
                }));
            }
        });

        // OSC sequence handler for media viewing
        this.terminal.parser.registerOscHandler(1337, (data) => {
            const parts = data.split('=');
            if (parts.length === 2) {
                const command = parts[0];
                const filePath = parts[1];

                switch (command) {
                    case 'ViewImage':
                        if (window.mediaHandler) {
                            window.mediaHandler.viewFile(filePath);
                        }
                        return true;
                    case 'PlayVideo':
                        if (window.mediaHandler) {
                            window.mediaHandler.playVideo(filePath);
                        }
                        return true;
                    case 'ViewHTML':
                        if (window.mediaHandler) {
                            window.mediaHandler.previewHTML(filePath);
                        }
                        return true;
                    case 'ViewMarkdown':
                        if (window.mediaHandler) {
                            window.mediaHandler.renderMarkdown(filePath);
                        }
                        return true;
                }
            }
            return false;
        });

        // Terminal resize handler
        this.terminal.onResize((size) => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN && this.sessionId) {
                this.websocket.send(JSON.stringify({
                    type: 'resize',
                    data: { cols: size.cols, rows: size.rows },
                    sessionId: this.sessionId,
                    timestamp: new Date().toISOString()
                }));
            }
        });

        // Window resize handler
        window.addEventListener('resize', () => {
            if (this.fitAddon) {
                this.fitAddon.fit();
            }
        });

        // Theme change handler
        document.addEventListener('htmx:afterSettle', () => {
            this.updateTheme();
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/terminal`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = (event) => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus('connected');

            // Send initial session request
            this.requestSession();
        };

        this.websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
                // Treat as raw terminal output
                if (event.data instanceof ArrayBuffer) {
                    const decoder = new TextDecoder('utf-8');
                    this.terminal.write(decoder.decode(event.data));
                } else {
                    this.terminal.write(event.data);
                }
            }
        };

        this.websocket.onclose = (event) => {
            console.log('WebSocket disconnected:', event.code, event.reason);
            this.isConnected = false;
            this.updateConnectionStatus('disconnected');

            // Attempt to reconnect after delay
            setTimeout(() => {
                if (!this.isConnected) {
                    this.connectWebSocket();
                }
            }, 3000);
        };

        this.websocket.onerror = (event) => {
            console.error('WebSocket error:', event);
            this.updateConnectionStatus('error');
        };
    }

    handleMessage(message) {
        const { type, data, sessionId, metadata } = message;

        switch (type) {
            case 'connected':
                console.log('WebSocket connected:', data);
                break;

            case 'output':
                // Ensure UTF-8 decoding for output
                if (data instanceof ArrayBuffer) {
                    const decoder = new TextDecoder('utf-8');
                    this.terminal.write(decoder.decode(data));
                } else if (typeof data === 'string') {
                    this.terminal.write(data);
                } else {
                    this.terminal.write(String(data));
                }
                break;

            case 'session_created':
                this.sessionId = sessionId;
                console.log('Terminal session created:', sessionId);
                this.updateSessionInfo(metadata);
                break;

            case 'session_info':
                this.updateSessionInfo(data);
                break;

            case 'media_view':
                this.handleMediaView(data, metadata);
                break;

            case 'ai_response':
                this.handleAIResponse(data, metadata);
                break;

            case 'recording_status':
                this.updateRecordingStatus(data);
                break;

            case 'error':
                console.error('Terminal error:', data);
                this.terminal.write(`\\r\\n\\x1b[31mError: ${data.message || data}\\x1b[0m\\r\\n`);
                break;

            default:
                console.log('Unknown message type:', type, data);
        }
    }

    requestSession() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            // Ensure terminal is fitted before sending dimensions
            if (this.fitAddon) {
                this.fitAddon.fit();
            }

            const message = {
                type: 'create_session',
                data: {
                    shell: 'bash', // Default shell
                    size: {
                        cols: this.terminal.cols,
                        rows: this.terminal.rows
                    }
                },
                timestamp: new Date().toISOString()
            };
            console.log('Sending create_session message:', message, `Terminal size: ${this.terminal.cols}x${this.terminal.rows}`);
            this.websocket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not ready, readyState:', this.websocket?.readyState);
        }
    }

    handleMediaView(data, metadata) {
        const overlay = document.getElementById('media-overlay');
        if (overlay) {
            // Use HTMX to load media content
            htmx.ajax('POST', '/api/media/render', {
                values: {
                    filePath: data.filePath,
                    mediaType: metadata.mediaType
                },
                target: '#media-overlay',
                swap: 'innerHTML'
            });
            overlay.classList.add('visible');
        }
    }

    handleAIResponse(data, metadata) {
        // Update AI sidebar with response
        htmx.trigger('#ai-sidebar', 'ai:response', {
            response: data,
            metadata: metadata
        });
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
            statusElement.className = `connection-status ${status}`;
        }
    }

    updateSessionInfo(info) {
        const sessionElement = document.getElementById('session-info');
        if (sessionElement && info) {
            sessionElement.textContent = `${info.shell} - ${info.workingDirectory || '~'}`;
        }
    }

    updateRecordingStatus(status) {
        // Update recording controls via HTMX
        htmx.ajax('GET', `/api/recording/status/${this.sessionId}`, {
            target: '#recording-controls',
            swap: 'innerHTML'
        });
    }

    updateTheme() {
        if (this.terminal) {
            const newTheme = {
                background: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-bg').trim(),
                foreground: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-fg').trim(),
                cursor: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-cursor').trim(),
                selection: getComputedStyle(document.documentElement)
                    .getPropertyValue('--terminal-selection').trim(),
            };

            this.terminal.options.theme = newTheme;
            this.terminal.refresh(0, this.terminal.rows - 1);
        }
    }

    // Public API methods
    write(data) {
        if (this.terminal) {
            this.terminal.write(data);
        }
    }

    clear() {
        if (this.terminal) {
            this.terminal.clear();
        }
    }

    resize() {
        if (this.fitAddon) {
            this.fitAddon.fit();
        }
    }

    focus() {
        if (this.terminal) {
            this.terminal.focus();
        }
    }
}

// Initialize terminal when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.webTerminal = new WebTerminal();

    // Focus terminal on page load
    setTimeout(() => {
        window.webTerminal.focus();
    }, 100);
});

// Export for use in other scripts
window.WebTerminal = WebTerminal;