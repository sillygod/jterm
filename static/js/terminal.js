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

        // T047: Lazy-loaded addon tracking
        this.webLinksAddon = null;
        this.searchAddon = null;
        this.unicode11Addon = null;
        this.addonsLoaded = {
            webLinks: false,
            search: false,
            unicode11: false
        };

        this.init();
    }

    init() {
        // Initialize xterm.js terminal with vibrant ANSI color palette
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
                // ANSI Colors - More vibrant palette matching modern terminals
                black: '#000000',
                red: '#E06C75',           // Brighter red
                green: '#98C379',         // Brighter green
                yellow: '#E5C07B',        // Brighter yellow
                blue: '#61AFEF',          // Brighter blue
                magenta: '#C678DD',       // Brighter magenta
                cyan: '#56B6C2',          // Brighter cyan
                white: '#ABB2BF',         // Brighter white
                brightBlack: '#5C6370',   // Bright black (gray)
                brightRed: '#E06C75',     // Bright red
                brightGreen: '#98C379',   // Bright green
                brightYellow: '#E5C07B',  // Bright yellow
                brightBlue: '#61AFEF',    // Bright blue
                brightMagenta: '#C678DD', // Bright magenta
                brightCyan: '#56B6C2',    // Bright cyan
                brightWhite: '#FFFFFF',   // Bright white
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

        // T047: Load FitAddon immediately (critical for terminal sizing)
        this.fitAddon = new FitAddon.FitAddon();
        this.terminal.loadAddon(this.fitAddon);

        // Get container and open terminal
        const container = document.getElementById(this.containerId);
        if (container) {
            this.terminal.open(container);
            this.fitAddon.fit();
        }

        this.setupEventListeners();
        this.connectWebSocket();

        // T047: Lazy-load non-critical addons after initial render
        // This reduces initial parsing time by ~10%
        setTimeout(() => {
            this.loadWebLinksAddon();
            this.loadUnicode11Addon();
            // SearchAddon loaded only when needed (e.g., Ctrl+F)
        }, 100);  // Small delay allows terminal to render first
    }

    setupEventListeners() {
        // Add a global document-level keydown listener to intercept shortcuts BEFORE browser handles them
        // This is necessary for shortcuts like Cmd+K that browsers capture very early
        const globalKeydownHandler = (event) => {
            // Only intercept when terminal has focus or event target is within terminal
            const terminalElement = document.getElementById('terminal');
            const isTerminalFocused = terminalElement &&
                (document.activeElement === terminalElement ||
                 terminalElement.contains(document.activeElement) ||
                 terminalElement.contains(event.target));

            if (!isTerminalFocused) {
                return; // Don't intercept when terminal is not focused
            }

            const shouldIntercept = (
                // Cmd/Ctrl + L (clear screen / tmux navigate)
                (event.key === 'l' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + H (backspace / tmux navigate)
                (event.key === 'h' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + J (tmux navigate)
                (event.key === 'j' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + K (tmux navigate / clear to top) - IMPORTANT: Capture early!
                (event.key === 'k' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + W (close window in browser, but delete word in terminal)
                (event.key === 'w' && (event.metaKey)) ||
                // Cmd/Ctrl + T (new tab in browser, but tmux command)
                (event.key === 't' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + N (new window in browser, but next in tmux)
                (event.key === 'n' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + P (print in browser, but previous in tmux)
                (event.key === 'p' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + [ and ] (browser navigation, but tmux escape/navigate)
                (event.key === '[' && (event.metaKey || event.ctrlKey)) ||
                (event.key === ']' && (event.metaKey || event.ctrlKey))
            );

            if (shouldIntercept) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation(); // Prevent other handlers from running
            }
        };

        // Add listener at capture phase (before bubble phase) for earliest interception
        document.addEventListener('keydown', globalKeydownHandler, { capture: true });

        // Store for cleanup
        this.globalKeydownHandler = globalKeydownHandler;

        // Capture keyboard events before browser handles them
        // This allows terminal shortcuts (like Cmd+L, Cmd+H) to work in tmux/vim
        this.terminal.attachCustomKeyEventHandler((event) => {
            // List of key combinations to intercept and send to terminal
            // These would normally be handled by the browser
            const shouldIntercept = (
                // Cmd/Ctrl + L (clear screen / tmux navigate)
                (event.key === 'l' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + H (backspace / tmux navigate)
                (event.key === 'h' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + J (tmux navigate)
                (event.key === 'j' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + K (tmux navigate / clear to top)
                (event.key === 'k' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + W (close window in browser, but delete word in terminal)
                (event.key === 'w' && (event.metaKey)) ||
                // Cmd/Ctrl + T (new tab in browser, but tmux command)
                (event.key === 't' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + N (new window in browser, but next in tmux)
                (event.key === 'n' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + P (print in browser, but previous in tmux)
                (event.key === 'p' && (event.metaKey || event.ctrlKey)) ||
                // Cmd/Ctrl + [ and ] (browser navigation, but tmux escape/navigate)
                (event.key === '[' && (event.metaKey || event.ctrlKey)) ||
                (event.key === ']' && (event.metaKey || event.ctrlKey))
            );

            if (shouldIntercept) {
                // Prevent browser from handling this event
                event.preventDefault();
                event.stopPropagation();
                // Return false to let xterm.js handle it normally
                return false;
            }

            // Allow browser to handle other shortcuts (Cmd+C for copy, Cmd+V for paste, etc.)
            return true;
        });

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

        // OSC sequence handler for media viewing and cat commands
        console.log('[Terminal] Registering OSC 1337 handler...');
        this.terminal.parser.registerOscHandler(1337, (data) => {
            console.log('[OSC 1337] Received data:', data);
            const parts = data.split('=');
            if (parts.length === 2) {
                const command = parts[0];
                const payload = parts[1];
                console.log('[OSC 1337] Command:', command, 'Payload:', payload);

                // Add test indicator
                if (payload === '/tmp/test.png') {
                    console.log('[OSC 1337] TEST OSC RECEIVED! Handler is working!');
                }

                switch (command) {
                    // Image editor handler (for imgcat command)
                    case 'ViewImage':
                        console.log('[OSC 1337] ViewImage - triggering image editor for:', payload);
                        this.handleImageViewer({
                            file_path: payload,
                            session_id: this.sessionId
                        });
                        return true;
                    case 'ViewImageURL':
                        console.log('[OSC 1337] ViewImageURL - triggering image editor for URL:', payload);
                        this.handleImageViewerURL({
                            url: payload,
                            session_id: this.sessionId
                        });
                        return true;
                    case 'PlayVideo':
                        if (window.mediaHandler) {
                            window.mediaHandler.playVideo(payload);
                        }
                        return true;
                    case 'ViewHTML':
                        if (window.mediaHandler) {
                            window.mediaHandler.previewHTML(payload);
                        }
                        return true;
                    case 'ViewMarkdown':
                        if (window.mediaHandler) {
                            window.mediaHandler.renderMarkdown(payload);
                        }
                        return true;

                    // T007: New cat command handlers
                    case 'ViewLog':
                        this.handleLogViewer(payload);
                        return true;
                    case 'ViewCert':
                        this.handleCertViewer(payload);
                        return true;
                    case 'QuerySQL':
                        this.handleSQLViewer(payload);
                        return true;
                    case 'HTTPRequest':
                        this.handleHTTPViewer(payload);
                        return true;
                    case 'ViewJWT':
                        this.handleJWTViewer(payload);
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

        // ResizeObserver to handle container size changes (e.g., sidebar toggle)
        // This automatically resizes the terminal when the container dimensions change
        const container = document.getElementById(this.containerId);
        if (container && window.ResizeObserver) {
            const resizeObserver = new ResizeObserver((entries) => {
                // Debounce resize to avoid excessive calls
                if (this.resizeTimeout) {
                    clearTimeout(this.resizeTimeout);
                }
                this.resizeTimeout = setTimeout(() => {
                    if (this.fitAddon) {
                        this.fitAddon.fit();
                    }
                }, 100);
            });
            resizeObserver.observe(container);
        }

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

            case 'ebook_viewer':
                // Handle ebook viewer OSC sequence
                this.handleEbookViewer(data);
                break;

            case 'image_viewer':
                // Handle image viewer OSC sequence
                this.handleImageViewer(data);
                break;

            case 'image_viewer_url':
                // Handle image viewer URL OSC sequence
                this.handleImageViewerURL(data);
                break;

            case 'performance_update':
                // Forward to performance monitor if available
                if (window.performanceMonitor && typeof window.performanceMonitor.handleServerMetrics === 'function') {
                    window.performanceMonitor.handleServerMetrics(data);
                }
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

    async handleEbookViewer(data) {
        /**
         * Handle ebook viewer OSC sequence.
         * Called when user runs `bookcat <file>` in terminal.
         */
        console.log('Ebook viewer triggered:', data);
        const { file_path } = data;

        try {
            // Call ebook processing API
            const response = await fetch('/api/ebooks/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ filePath: file_path })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to process ebook');
            }

            const result = await response.json();

            // Check if ebook-viewer.js is loaded, if not load it
            if (typeof window.ebookViewer === 'undefined') {
                console.log('Loading ebook-viewer.js...');
                await this.loadScript('/static/js/ebook-viewer.js');
            }

            // Open ebook viewer with the processed ebook metadata
            if (window.ebookViewer) {
                // Check if PDF is encrypted and requires password
                if (result.is_encrypted) {
                    console.log('PDF is encrypted, showing password prompt');
                    window.ebookViewer.showPasswordPrompt(result.id, file_path, {});
                } else {
                    // Not encrypted, render viewer directly
                    await window.ebookViewer.renderViewer(result);
                }
            } else {
                console.error('EbookViewer not available');
            }

        } catch (error) {
            console.error('Error opening ebook:', error);
            this.terminal.write(`\r\n\x1b[31mError opening ebook: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleImageViewer(data) {
        /**
         * Handle image viewer OSC sequence.
         * Called when user runs `imgcat <file>` in terminal.
         */
        console.log('[ImageViewer] Image viewer triggered:', data);
        const { file_path, session_id } = data;

        try {
            // Call image editor API to load the image
            const response = await fetch('/api/v1/image-editor/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    source_type: 'file',
                    source_path: file_path,
                    terminal_session_id: session_id
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load image');
            }

            const result = await response.json();
            console.log('[ImageViewer] Image loaded:', result);

            // Load dependencies first
            await this.loadImageEditorDependencies();

            // Fetch the editor component HTML
            const componentResponse = await fetch(`/api/v1/image-editor/component/${result.session_id}`);
            if (!componentResponse.ok) {
                throw new Error('Failed to load editor component');
            }
            const componentHTML = await componentResponse.text();

            // Get or create overlay
            let overlay = document.getElementById('media-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'media-overlay';
                overlay.className = 'media-overlay';
                document.body.appendChild(overlay);
            }

            // Insert editor HTML
            overlay.innerHTML = componentHTML;
            overlay.classList.add('visible');

            // Initialize the image editor
            if (window.ImageEditor) {
                window.ImageEditor.init(result.session_id);
            } else {
                throw new Error('ImageEditor not loaded');
            }

            // Set up event listeners for toolbar controls
            setTimeout(() => {
                const toolButtons = document.querySelectorAll('.tool-btn[data-tool]');
                const editorElement = document.getElementById(`image-editor-${result.session_id}`);

                console.log('[ImageViewer] Setting up event listeners, found', toolButtons.length, 'tool buttons');

                if (editorElement) {
                    // Tool buttons
                    toolButtons.forEach(btn => {
                        btn.addEventListener('click', function(e) {
                            const tool = this.getAttribute('data-tool');
                            console.log('[ImageViewer] Tool button clicked:', tool);

                            const event = new CustomEvent('toolChange', {
                                detail: { tool: tool },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    });

                    // Color picker
                    const colorPicker = document.getElementById(`stroke-color-${result.session_id}`);
                    if (colorPicker) {
                        colorPicker.addEventListener('input', function(e) {
                            console.log('[ImageViewer] Color changed:', this.value);
                            const event = new CustomEvent('colorChange', {
                                detail: { color: this.value },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    // Color presets
                    const colorPresets = document.querySelectorAll('.color-preset[data-color]');
                    colorPresets.forEach(preset => {
                        preset.addEventListener('click', function(e) {
                            const color = this.getAttribute('data-color');
                            console.log('[ImageViewer] Color preset clicked:', color);

                            if (colorPicker) {
                                colorPicker.value = color;
                            }

                            const event = new CustomEvent('colorChange', {
                                detail: { color: color },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    });

                    // Stroke width
                    const strokeWidth = document.getElementById(`stroke-width-${result.session_id}`);
                    if (strokeWidth) {
                        strokeWidth.addEventListener('input', function(e) {
                            console.log('[ImageViewer] Stroke width changed:', this.value);
                            const event = new CustomEvent('strokeWidthChange', {
                                detail: { width: parseInt(this.value) },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    // Fill toggle
                    const fillCheckbox = document.getElementById(`fill-shape-${result.session_id}`);
                    if (fillCheckbox) {
                        fillCheckbox.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Fill toggle changed:', this.checked);
                            const event = new CustomEvent('fillToggle', {
                                detail: { fill: this.checked },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    // Fill color
                    const fillColor = document.getElementById(`fill-color-${result.session_id}`);
                    if (fillColor) {
                        fillColor.addEventListener('input', function(e) {
                            console.log('[ImageViewer] Fill color changed:', this.value);
                            const event = new CustomEvent('fillColorChange', {
                                detail: { color: this.value },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    // Text formatting controls (T131-T134)
                    const fontSize = document.getElementById(`font-size-${result.session_id}`);
                    if (fontSize) {
                        fontSize.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Font size changed:', this.value);
                            const event = new CustomEvent('fontSizeChange', {
                                detail: { size: parseInt(this.value) },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    const boldBtn = document.getElementById(`text-bold-${result.session_id}`);
                    if (boldBtn) {
                        boldBtn.addEventListener('click', function(e) {
                            const isActive = this.classList.contains('active');
                            console.log('[ImageViewer] Bold toggled:', isActive);
                            const event = new CustomEvent('textBoldToggle', {
                                detail: { bold: isActive },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    const italicBtn = document.getElementById(`text-italic-${result.session_id}`);
                    if (italicBtn) {
                        italicBtn.addEventListener('click', function(e) {
                            const isActive = this.classList.contains('active');
                            console.log('[ImageViewer] Italic toggled:', isActive);
                            const event = new CustomEvent('textItalicToggle', {
                                detail: { italic: isActive },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    const textBgCheckbox = document.getElementById(`text-background-${result.session_id}`);
                    if (textBgCheckbox) {
                        textBgCheckbox.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Text background toggled:', this.checked);
                            const event = new CustomEvent('textBackgroundToggle', {
                                detail: { background: this.checked },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    console.log('[ImageViewer] Event listeners set up successfully');
                }
            }, 300); // Wait for editor to fully initialize

            console.log('[ImageViewer] Image editor panel opened');

        } catch (error) {
            console.error('[ImageViewer] Error opening image:', error);
            this.terminal.write(`\r\n\x1b[31mError opening image: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleImageViewerURL(data) {
        /**
         * Handle image viewer URL OSC sequence.
         * Called when user runs `imgcat <http://url>` in terminal.
         */
        console.log('[ImageViewer] Image viewer URL triggered:', data);
        const { url, session_id } = data;

        try {
            // Call image editor API to load the image from URL
            const response = await fetch('/api/v1/image-editor/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    source_type: 'url',
                    source_path: url,
                    terminal_session_id: session_id
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load image from URL');
            }

            const result = await response.json();
            console.log('[ImageViewer] Image loaded from URL:', result);

            // Load dependencies first
            await this.loadImageEditorDependencies();

            // Fetch the editor component HTML
            const componentResponse = await fetch(`/api/v1/image-editor/component/${result.session_id}`);
            if (!componentResponse.ok) {
                throw new Error('Failed to load editor component');
            }
            const componentHTML = await componentResponse.text();

            // Get or create overlay
            let overlay = document.getElementById('media-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'media-overlay';
                overlay.className = 'media-overlay';
                document.body.appendChild(overlay);
            }

            // Insert editor HTML
            overlay.innerHTML = componentHTML;
            overlay.classList.add('visible');

            // Initialize the image editor
            if (window.ImageEditor) {
                window.ImageEditor.init(result.session_id);
            } else {
                throw new Error('ImageEditor not loaded');
            }

            // Set up event listeners for toolbar controls
            setTimeout(() => {
                const toolButtons = document.querySelectorAll('.tool-btn[data-tool]');
                const editorElement = document.getElementById(`image-editor-${result.session_id}`);

                console.log('[ImageViewer] Setting up event listeners for URL image, found', toolButtons.length, 'tool buttons');

                if (editorElement) {
                    // Tool buttons
                    toolButtons.forEach(btn => {
                        btn.addEventListener('click', function(e) {
                            const tool = this.getAttribute('data-tool');
                            console.log('[ImageViewer] Tool button clicked:', tool);
                            const event = new CustomEvent('toolSelected', {
                                detail: { tool: tool },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    });

                    // Color pickers
                    const strokeColorInput = document.getElementById('stroke-color');
                    const fillColorInput = document.getElementById('fill-color');

                    if (strokeColorInput) {
                        strokeColorInput.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Stroke color changed:', this.value);
                            const event = new CustomEvent('strokeColorChange', {
                                detail: { color: this.value },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    if (fillColorInput) {
                        fillColorInput.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Fill color changed:', this.value);
                            const event = new CustomEvent('fillColorChange', {
                                detail: { color: this.value },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    // Text background toggle
                    const textBgToggle = document.getElementById('text-background');
                    if (textBgToggle) {
                        textBgToggle.addEventListener('change', function(e) {
                            console.log('[ImageViewer] Text background toggled:', this.checked);
                            const event = new CustomEvent('textBackgroundToggle', {
                                detail: { background: this.checked },
                                bubbles: true
                            });
                            editorElement.dispatchEvent(event);
                        });
                    }

                    console.log('[ImageViewer] Event listeners set up successfully for URL image');
                }
            }, 300); // Wait for editor to fully initialize

            console.log('[ImageViewer] Image editor panel opened for URL');

        } catch (error) {
            console.error('[ImageViewer] Error opening image from URL:', error);
            this.terminal.write(`\r\n\x1b[31mError loading image from URL: ${error.message}\x1b[0m\r\n`);
        }
    }

    // T007: Cat command viewer handlers

    async handleLogViewer(payload) {
        /**
         * Handle log viewer OSC sequence.
         * Called when user runs `logcat <file>` in terminal.
         * Payload format: JSON with file path and optional filters
         */
        console.log('Log viewer triggered:', payload);

        try {
            const params = JSON.parse(payload);

            // Load CSS files if not already loaded
            if (!document.querySelector('link[href="/static/css/log-viewer.css"]')) {
                console.log('Loading log-viewer CSS...');
                await this.loadCSS('/static/css/log-viewer.css');
            }

            // Load BaseViewer first if not already loaded
            if (typeof window.BaseViewer === 'undefined') {
                console.log('Loading base-viewer.js...');
                await this.loadScript('/static/js/base-viewer.js');
            }

            // Then load log-viewer.js if not already loaded
            if (typeof window.LogViewer === 'undefined') {
                console.log('Loading log-viewer.js...');
                await this.loadScript('/static/js/log-viewer.js');
            }

            // Initialize and show log viewer
            if (window.LogViewer) {
                const viewer = new window.LogViewer(params);
                await viewer.open();
            } else {
                throw new Error('LogViewer not available after loading');
            }

        } catch (error) {
            console.error('Error opening log viewer:', error);
            this.terminal.write(`\r\n\x1b[31mError opening log viewer: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleCertViewer(payload) {
        /**
         * Handle certificate viewer OSC sequence.
         * Called when user runs `certcat <url|file>` in terminal.
         * Payload format: JSON with URL/file path and options
         */
        console.log('Certificate viewer triggered:', payload);

        try {
            const params = JSON.parse(payload);

            // Load BaseViewer first if not already loaded
            if (typeof window.BaseViewer === 'undefined') {
                console.log('Loading base-viewer.js...');
                await this.loadScript('/static/js/base-viewer.js');
            }

            // Lazy-load cert-viewer.js if not already loaded
            if (typeof window.CertViewer === 'undefined') {
                console.log('Loading cert-viewer.js...');
                await this.loadScript('/static/js/cert-viewer.js');
            }

            // Initialize and show certificate viewer
            if (window.CertViewer) {
                const viewer = new window.CertViewer(params);
                await viewer.open();
            } else {
                throw new Error('CertViewer not available after loading');
            }

        } catch (error) {
            console.error('Error opening certificate viewer:', error);
            this.terminal.write(`\r\n\x1b[31mError opening certificate viewer: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleSQLViewer(payload) {
        /**
         * Handle SQL viewer OSC sequence.
         * Called when user runs `sqlcat <options>` in terminal.
         * Payload format: JSON with database connection info and query
         */
        console.log('SQL viewer triggered:', payload);

        try {
            const params = JSON.parse(payload);

            // Load CSS files if not already loaded
            if (!document.querySelector('link[href="/static/css/shared-viewers.css"]')) {
                console.log('Loading shared-viewers CSS...');
                await this.loadCSS('/static/css/shared-viewers.css');
            }
            if (!document.querySelector('link[href="/static/css/sql-viewer.css"]')) {
                console.log('Loading sql-viewer CSS...');
                await this.loadCSS('/static/css/sql-viewer.css');
            }

            // Load Chart.js if not already loaded (for visualization)
            if (typeof window.Chart === 'undefined') {
                console.log('Loading Chart.js...');
                await this.loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js');
            }

            // Load BaseViewer first if not already loaded
            if (typeof window.BaseViewer === 'undefined') {
                console.log('Loading base-viewer.js...');
                await this.loadScript('/static/js/base-viewer.js');
            }

            // Lazy-load sql-viewer.js if not already loaded
            if (typeof window.SQLViewer === 'undefined') {
                console.log('Loading sql-viewer.js...');
                await this.loadScript('/static/js/sql-viewer.js');
            }

            // Initialize and show SQL viewer
            if (window.SQLViewer) {
                const viewer = new window.SQLViewer(params);
                await viewer.open();
            } else {
                throw new Error('SQLViewer not available after loading');
            }

        } catch (error) {
            console.error('Error opening SQL viewer:', error);
            this.terminal.write(`\r\n\x1b[31mError opening SQL viewer: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleHTTPViewer(payload) {
        /**
         * Handle HTTP request viewer OSC sequence.
         * Called when user runs `curlcat <url>` in terminal.
         * Payload format: JSON with request details
         */
        console.log('HTTP viewer triggered:', payload);

        try {
            const params = JSON.parse(payload);

            // Load CSS files if not already loaded
            if (!document.querySelector('link[href="/static/css/curl-viewer.css"]')) {
                console.log('Loading curl-viewer CSS...');
                await this.loadCSS('/static/css/curl-viewer.css');
            }

            if (!document.querySelector('link[href="/static/css/shared-viewers.css"]')) {
                console.log('Loading shared-viewers CSS...');
                await this.loadCSS('/static/css/shared-viewers.css');
            }

            // Load BaseViewer first if not already loaded
            if (typeof window.BaseViewer === 'undefined') {
                console.log('Loading base-viewer.js...');
                await this.loadScript('/static/js/base-viewer.js');
            }

            // Lazy-load curl-viewer.js if not already loaded
            if (typeof window.CurlViewer === 'undefined') {
                console.log('Loading curl-viewer.js...');
                await this.loadScript('/static/js/curl-viewer.js');
            }

            // Initialize and show HTTP viewer
            if (window.CurlViewer) {
                const viewer = new window.CurlViewer(params);
                await viewer.open();
            } else {
                throw new Error('CurlViewer not available after loading');
            }

        } catch (error) {
            console.error('Error opening HTTP viewer:', error);
            this.terminal.write(`\r\n\x1b[31mError opening HTTP viewer: ${error.message}\x1b[0m\r\n`);
        }
    }

    async handleJWTViewer(payload) {
        /**
         * Handle JWT viewer OSC sequence.
         * Called when user runs `jwtcat <token>` in terminal.
         * Payload format: JWT token string
         */
        console.log('JWT viewer triggered:', payload);

        try {
            // Load CSS files if not already loaded
            if (!document.querySelector('link[href="/static/css/jwt-viewer.css"]')) {
                console.log('Loading jwt-viewer CSS...');
                await this.loadCSS('/static/css/jwt-viewer.css');
            }

            if (!document.querySelector('link[href="/static/css/shared-viewers.css"]')) {
                console.log('Loading shared-viewers CSS...');
                await this.loadCSS('/static/css/shared-viewers.css');
            }

            // Load BaseViewer first if not already loaded
            if (typeof window.BaseViewer === 'undefined') {
                console.log('Loading base-viewer.js...');
                await this.loadScript('/static/js/base-viewer.js');
            }

            // Lazy-load jwt-viewer.js if not already loaded
            if (typeof window.JWTViewer === 'undefined') {
                console.log('Loading jwt-viewer.js...');
                await this.loadScript('/static/js/jwt-viewer.js');
                console.log('jwt-viewer.js loaded. Checking window.JWTViewer:', typeof window.JWTViewer);
            } else {
                console.log('JWTViewer already loaded');
            }

            // Initialize and show JWT viewer
            if (window.JWTViewer) {
                console.log('Creating JWTViewer instance with payload:', payload);
                const viewer = new window.JWTViewer(payload);
                await viewer.open();
            } else {
                console.error('window.JWTViewer is:', window.JWTViewer);
                console.error('Available window properties:', Object.keys(window).filter(k => k.includes('Viewer')));
                throw new Error('JWTViewer not available after loading');
            }

        } catch (error) {
            console.error('Error opening JWT viewer:', error);
            this.terminal.write(`\r\n\x1b[31mError opening JWT viewer: ${error.message}\x1b[0m\r\n`);
        }
    }

    loadScript(src) {
        /**
         * Dynamically load a JavaScript file.
         */
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    loadCSS(href) {
        /**
         * Dynamically load a CSS file.
         */
        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.onload = resolve;
            link.onerror = reject;
            document.head.appendChild(link);
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
                // Keep vibrant ANSI colors even when theme changes
                black: '#000000',
                red: '#E06C75',
                green: '#98C379',
                yellow: '#E5C07B',
                blue: '#61AFEF',
                magenta: '#C678DD',
                cyan: '#56B6C2',
                white: '#ABB2BF',
                brightBlack: '#5C6370',
                brightRed: '#E06C75',
                brightGreen: '#98C379',
                brightYellow: '#E5C07B',
                brightBlue: '#61AFEF',
                brightMagenta: '#C678DD',
                brightCyan: '#56B6C2',
                brightWhite: '#FFFFFF',
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

    // T047: Lazy-loading methods for xterm.js addons

    async loadWebLinksAddon() {
        if (this.addonsLoaded.webLinks) return;

        try {
            // Dynamically load WebLinksAddon script
            await this.loadScript('https://cdn.jsdelivr.net/npm/xterm-addon-web-links@0.9.0/lib/xterm-addon-web-links.js');

            this.webLinksAddon = new WebLinksAddon.WebLinksAddon();
            this.terminal.loadAddon(this.webLinksAddon);
            this.addonsLoaded.webLinks = true;

            console.debug('[T047] WebLinksAddon loaded');
        } catch (error) {
            console.error('Failed to load WebLinksAddon:', error);
        }
    }

    async loadSearchAddon() {
        if (this.addonsLoaded.search) return;

        try {
            // Dynamically load SearchAddon script
            await this.loadScript('https://cdn.jsdelivr.net/npm/xterm-addon-search@0.13.0/lib/xterm-addon-search.js');

            this.searchAddon = new SearchAddon.SearchAddon();
            this.terminal.loadAddon(this.searchAddon);
            this.addonsLoaded.search = true;

            console.debug('[T047] SearchAddon loaded');
        } catch (error) {
            console.error('Failed to load SearchAddon:', error);
        }
    }

    async loadUnicode11Addon() {
        if (this.addonsLoaded.unicode11) return;

        try {
            // Dynamically load Unicode11Addon script
            await this.loadScript('https://cdn.jsdelivr.net/npm/xterm-addon-unicode11@0.6.0/lib/xterm-addon-unicode11.js');

            this.unicode11Addon = new Unicode11Addon.Unicode11Addon();
            this.terminal.loadAddon(this.unicode11Addon);
            this.terminal.unicode.activeVersion = '11';
            this.addonsLoaded.unicode11 = true;

            console.debug('[T047] Unicode11Addon loaded');
        } catch (error) {
            console.error('Failed to load Unicode11Addon:', error);
        }
    }

    loadScript(src) {
        return new Promise((resolve, reject) => {
            // Check if script already exists
            const existingScript = document.querySelector(`script[src="${src}"]`);
            if (existingScript) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // Test function to manually send OSC sequence
    testOSC() {
        console.log('[TEST] Sending test OSC sequence to terminal...');
        // ESC ] 1337 ; ViewImage=/tmp/test.png BEL
        this.terminal.write('\x1b]1337;ViewImage=/tmp/test.png\x07');
        console.log('[TEST] Test OSC sequence sent');
    }

    async loadImageEditorDependencies() {
        /**
         * Load all required dependencies for image editor in correct order.
         */
        console.log('[ImageViewer] Loading image editor dependencies...');

        // 1. Load Fabric.js
        if (typeof window.fabric === 'undefined') {
            console.log('[ImageViewer] Loading Fabric.js...');
            await this.loadScript('/static/js/vendor/fabric.min.js');
        }

        // 2. Load DrawingTools (must be loaded before ImageEditor)
        if (typeof window.DrawingTools === 'undefined') {
            console.log('[ImageViewer] Loading drawing-tools.js...');
            await this.loadScript('/static/js/drawing-tools.js');
        }

        // 3. Load FilterEngine
        if (typeof window.FilterEngine === 'undefined') {
            console.log('[ImageViewer] Loading filter-engine.js...');
            await this.loadScript('/static/js/filter-engine.js');
        }

        // 4. Load ImageEditor
        if (typeof window.ImageEditor === 'undefined') {
            console.log('[ImageViewer] Loading image-editor.js...');
            await this.loadScript('/static/js/image-editor.js');
        }

        console.log('[ImageViewer] All dependencies loaded');
    }

    loadCSS(href) {
        /**
         * Dynamically load a CSS file.
         */
        return new Promise((resolve, reject) => {
            // Check if CSS already exists
            const existingLink = document.querySelector(`link[href="${href}"]`);
            if (existingLink) {
                resolve();
                return;
            }

            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            link.onload = resolve;
            link.onerror = reject;
            document.head.appendChild(link);
        });
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

// Global test function for OSC sequences
window.testOSC = function() {
    console.log('[TEST] Testing OSC sequence handler...');
    if (window.webTerminal && window.webTerminal.testOSC) {
        window.webTerminal.testOSC();
    } else {
        console.error('[TEST] Terminal not found or not initialized yet!');
    }
};

// Global close function for image editor
window.closeImageEditor = function(sessionId) {
    console.log('[ImageEditor] Closing editor for session:', sessionId);

    // Remove the editor element
    const editor = document.getElementById(`image-editor-${sessionId}`);
    if (editor) {
        editor.remove();
    }

    // Hide the overlay
    const overlay = document.getElementById('media-overlay');
    if (overlay) {
        overlay.classList.remove('visible');
        overlay.innerHTML = '';
    }

    // Clean up ImageEditor instance
    if (window.ImageEditor && window.ImageEditor.instances) {
        delete window.ImageEditor.instances[sessionId];
    }
};

// Export for use in other scripts
window.WebTerminal = WebTerminal;
