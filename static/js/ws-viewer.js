/**
 * WebSocket Client Viewer (WsViewer)
 *
 * Provides interactive interface for:
 * - Connecting to WebSocket servers
 * - Sending and receiving messages in real-time
 * - Viewing message history with timestamps
 * - Connection status monitoring
 */

class WsViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `ws-viewer-${Date.now()}`;
        super(viewerId, 'ws');

        this.url = params.url || '';
        this.headers = params.headers || [];
        this.protocol = params.protocol || '';

        this.baseUrl = '/ws';
        this.connectionId = null;
        this.connected = false;
        this.websocket = null;
        this.messages = [];
    }

    async open() {
        /**
         * Open the WebSocket viewer
         */
        try {
            // Create viewer UI
            await this.createViewer();
            super.init();
            this.show();

            // Populate form with initial data if provided
            if (this.url) {
                this.populateForm();
                // Auto-connect if URL provided
                await this.connect();
            }

            // Attach event listeners
            this.attachEventListeners();

        } catch (error) {
            console.error('Failed to open WebSocket viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the WebSocket viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container ws-viewer-container" id="${this.viewerId}-container">
                    <div class="ws-viewer">
                        ${this.getViewerContent()}
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', viewerHtml);
        this.overlay = document.getElementById(`${this.viewerId}-overlay`);
        this.container = document.getElementById(`${this.viewerId}-container`);
    }

    getViewerContent() {
        return `
            <div class="viewer-header ws-viewer-header">
                <h2 class="viewer-title">
                    <span class="viewer-icon">🔌</span>
                    WebSocket Client
                </h2>
                <div class="connection-status" id="${this.viewerId}-status">
                    <span class="status-indicator disconnected"></span>
                    <span class="status-text">Disconnected</span>
                </div>
                <button class="viewer-btn-close" title="Close (Esc)">✕</button>
            </div>
            <div class="viewer-layout">
                ${this.getConnectionPanel()}
                ${this.getMessagesPanel()}
            </div>
        `;
    }

    getConnectionPanel() {
        return `
            <div class="connection-panel">
                <div class="panel-header">
                    <h3>Connection</h3>
                </div>
                <div class="connection-form">
                    <div class="form-group">
                        <label for="${this.viewerId}-ws-url">WebSocket URL</label>
                        <input type="text"
                               id="${this.viewerId}-ws-url"
                               class="ws-url-input"
                               placeholder="ws://echo.websocket.org"
                               value="${this.escapeHtml(this.url)}">
                        <small class="help-text">Enter WebSocket URL (ws:// or wss://)</small>
                    </div>

                    <div class="form-group">
                        <label for="${this.viewerId}-ws-headers">Headers (optional)</label>
                        <textarea id="${this.viewerId}-ws-headers"
                                  rows="4"
                                  placeholder="Authorization: Bearer token&#10;X-Custom-Header: value"></textarea>
                        <small class="help-text">One header per line: Key: Value</small>
                    </div>

                    <div class="form-group">
                        <label for="${this.viewerId}-ws-protocol">Subprotocol (optional)</label>
                        <input type="text"
                               id="${this.viewerId}-ws-protocol"
                               placeholder="chat, echo, etc."
                               value="${this.escapeHtml(this.protocol)}">
                        <small class="help-text">WebSocket subprotocol name</small>
                    </div>

                    <div class="connection-actions">
                        <button id="${this.viewerId}-connect-btn" class="btn-primary">Connect</button>
                        <button id="${this.viewerId}-disconnect-btn" class="btn-danger" disabled>Disconnect</button>
                    </div>

                    <div class="connection-info" id="${this.viewerId}-connection-info" style="display: none;">
                        <h4>Connection Info</h4>
                        <div class="info-row">
                            <span class="info-label">Connection ID:</span>
                            <span class="info-value" id="${this.viewerId}-connection-id">-</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Protocol:</span>
                            <span class="info-value" id="${this.viewerId}-protocol-info">-</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Connected At:</span>
                            <span class="info-value" id="${this.viewerId}-connected-at">-</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    getMessagesPanel() {
        return `
            <div class="messages-panel">
                <div class="panel-header">
                    <h3>Messages</h3>
                    <button id="${this.viewerId}-clear-messages" class="btn-secondary btn-small">Clear</button>
                </div>
                <div id="${this.viewerId}-messages-container" class="messages-container">
                    <p class="empty-state">Connect to start sending and receiving messages</p>
                </div>
                <div class="message-input-container">
                    <textarea id="${this.viewerId}-message-input"
                              class="message-input"
                              placeholder="Type your message here..."
                              rows="3"
                              disabled></textarea>
                    <button id="${this.viewerId}-send-btn" class="btn-primary" disabled>Send</button>
                </div>
            </div>
        `;
    }

    populateForm() {
        /**
         * Populate form with initial data
         */
        const urlInput = document.getElementById(`${this.viewerId}-ws-url`);
        const headersInput = document.getElementById(`${this.viewerId}-ws-headers`);
        const protocolInput = document.getElementById(`${this.viewerId}-ws-protocol`);

        if (urlInput && this.url) {
            urlInput.value = this.url;
        }

        if (headersInput && this.headers.length > 0) {
            headersInput.value = this.headers.join('\n');
        }

        if (protocolInput && this.protocol) {
            protocolInput.value = this.protocol;
        }
    }

    attachEventListeners() {
        /**
         * Attach event listeners to interactive elements
         */
        // Connect button
        const connectBtn = document.getElementById(`${this.viewerId}-connect-btn`);
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connect());
        }

        // Disconnect button
        const disconnectBtn = document.getElementById(`${this.viewerId}-disconnect-btn`);
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnect());
        }

        // Send button
        const sendBtn = document.getElementById(`${this.viewerId}-send-btn`);
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // Clear messages button
        const clearBtn = document.getElementById(`${this.viewerId}-clear-messages`);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearMessages());
        }

        // Message input - send on Ctrl+Enter
        const messageInput = document.getElementById(`${this.viewerId}-message-input`);
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // URL input - connect on Enter
        const urlInput = document.getElementById(`${this.viewerId}-ws-url`);
        if (urlInput) {
            urlInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !this.connected) {
                    e.preventDefault();
                    this.connect();
                }
            });
        }
    }

    async connect() {
        /**
         * Connect to WebSocket server
         */
        if (this.connected) {
            this.showError('Already connected');
            return;
        }

        try {
            // Get form values
            const urlInput = document.getElementById(`${this.viewerId}-ws-url`);
            const headersInput = document.getElementById(`${this.viewerId}-ws-headers`);
            const protocolInput = document.getElementById(`${this.viewerId}-ws-protocol`);

            const url = urlInput?.value.trim();
            if (!url) {
                this.showError('Please enter a WebSocket URL');
                return;
            }

            // Validate URL
            if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
                this.showError('URL must start with ws:// or wss://');
                return;
            }

            // Parse headers
            const headersText = headersInput?.value.trim() || '';
            const headers = headersText.split('\n')
                .map(line => line.trim())
                .filter(line => line.length > 0);

            const protocol = protocolInput?.value.trim() || null;

            // Show loading state
            this.showLoading('Connecting...');

            // Call backend API to connect
            const response = await fetch(`${this.baseUrl}/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    headers: headers,
                    protocol: protocol
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Connection failed');
            }

            const data = await response.json();
            this.connectionId = data.connection_id;
            this.connected = true;

            // Update UI
            this.updateConnectionStatus(true);
            this.updateConnectionInfo(data);
            this.addSystemMessage(`Connected to ${url}`);

            // Start WebSocket stream
            this.startWebSocketStream();

            this.hideLoading();

        } catch (error) {
            console.error('Connection error:', error);
            this.showError(error.message);
            this.hideLoading();
        }
    }

    async disconnect() {
        /**
         * Disconnect from WebSocket server
         */
        if (!this.connected || !this.connectionId) {
            return;
        }

        try {
            // Close frontend WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }

            // Call backend API to disconnect
            const response = await fetch(`${this.baseUrl}/disconnect?connection_id=${this.connectionId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const error = await response.json();
                console.warn('Disconnect warning:', error.detail);
            }

            // Update state
            this.connected = false;
            this.connectionId = null;

            // Update UI
            this.updateConnectionStatus(false);
            this.addSystemMessage('Disconnected');

        } catch (error) {
            console.error('Disconnect error:', error);
            // Still update UI even if backend call fails
            this.connected = false;
            this.connectionId = null;
            this.updateConnectionStatus(false);
            this.addSystemMessage('Disconnected (with errors)');
        }
    }

    startWebSocketStream() {
        /**
         * Start WebSocket connection to backend for message streaming
         */
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.baseUrl}/stream/${this.connectionId}`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('WebSocket stream connected');
        };

        this.websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.addSystemMessage('WebSocket error occurred', 'error');
        };

        this.websocket.onclose = () => {
            console.log('WebSocket stream closed');
            if (this.connected) {
                this.addSystemMessage('Connection closed', 'error');
                this.connected = false;
                this.updateConnectionStatus(false);
            }
        };
    }

    handleWebSocketMessage(data) {
        /**
         * Handle incoming WebSocket message from backend
         */
        const { type, message, timestamp } = data;

        switch (type) {
            case 'received':
                this.addMessage(message, 'received', timestamp);
                break;
            case 'sent':
                // Message already displayed when sent
                break;
            case 'status':
                this.addSystemMessage(message, 'status');
                break;
            case 'error':
                this.addSystemMessage(message, 'error');
                break;
        }
    }

    async sendMessage() {
        /**
         * Send a message through the WebSocket
         */
        if (!this.connected || !this.websocket) {
            this.showError('Not connected');
            return;
        }

        const messageInput = document.getElementById(`${this.viewerId}-message-input`);
        const message = messageInput?.value.trim();

        if (!message) {
            return;
        }

        try {
            // Send through frontend WebSocket
            this.websocket.send(JSON.stringify({
                type: 'message',
                message: message
            }));

            // Add to UI immediately
            this.addMessage(message, 'sent');

            // Clear input
            messageInput.value = '';

        } catch (error) {
            console.error('Send error:', error);
            this.showError('Failed to send message');
        }
    }

    addMessage(text, type, timestamp = null) {
        /**
         * Add a message to the messages panel
         */
        const container = document.getElementById(`${this.viewerId}-messages-container`);
        if (!container) return;

        // Remove empty state if present
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;

        const time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();

        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-type">${type === 'sent' ? 'Sent' : 'Received'}</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-body">${this.escapeHtml(text)}</div>
        `;

        container.appendChild(messageEl);
        container.scrollTop = container.scrollHeight;

        // Store in messages array
        this.messages.push({ text, type, timestamp: timestamp || new Date().toISOString() });
    }

    addSystemMessage(text, type = 'status') {
        /**
         * Add a system message to the messages panel
         */
        const container = document.getElementById(`${this.viewerId}-messages-container`);
        if (!container) return;

        // Remove empty state if present
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const messageEl = document.createElement('div');
        messageEl.className = `message message-system message-${type}`;

        const time = new Date().toLocaleTimeString();

        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-type">System</span>
                <span class="message-time">${time}</span>
            </div>
            <div class="message-body">${this.escapeHtml(text)}</div>
        `;

        container.appendChild(messageEl);
        container.scrollTop = container.scrollHeight;
    }

    clearMessages() {
        /**
         * Clear all messages from the messages panel
         */
        const container = document.getElementById(`${this.viewerId}-messages-container`);
        if (!container) return;

        container.innerHTML = '<p class="empty-state">Messages cleared</p>';
        this.messages = [];
    }

    updateConnectionStatus(connected) {
        /**
         * Update connection status indicator
         */
        const statusContainer = document.getElementById(`${this.viewerId}-status`);
        const indicator = statusContainer?.querySelector('.status-indicator');
        const text = statusContainer?.querySelector('.status-text');
        const connectBtn = document.getElementById(`${this.viewerId}-connect-btn`);
        const disconnectBtn = document.getElementById(`${this.viewerId}-disconnect-btn`);
        const messageInput = document.getElementById(`${this.viewerId}-message-input`);
        const sendBtn = document.getElementById(`${this.viewerId}-send-btn`);

        if (connected) {
            indicator?.classList.remove('disconnected');
            indicator?.classList.add('connected');
            if (text) text.textContent = 'Connected';

            if (connectBtn) connectBtn.disabled = true;
            if (disconnectBtn) disconnectBtn.disabled = false;
            if (messageInput) messageInput.disabled = false;
            if (sendBtn) sendBtn.disabled = false;
        } else {
            indicator?.classList.remove('connected');
            indicator?.classList.add('disconnected');
            if (text) text.textContent = 'Disconnected';

            if (connectBtn) connectBtn.disabled = false;
            if (disconnectBtn) disconnectBtn.disabled = true;
            if (messageInput) messageInput.disabled = true;
            if (sendBtn) sendBtn.disabled = true;
        }
    }

    updateConnectionInfo(data) {
        /**
         * Update connection info display
         */
        const infoContainer = document.getElementById(`${this.viewerId}-connection-info`);
        if (!infoContainer) return;

        infoContainer.style.display = 'block';

        const connectionIdEl = document.getElementById(`${this.viewerId}-connection-id`);
        const protocolEl = document.getElementById(`${this.viewerId}-protocol-info`);
        const connectedAtEl = document.getElementById(`${this.viewerId}-connected-at`);

        if (connectionIdEl) connectionIdEl.textContent = data.connection_id.substring(0, 8) + '...';
        if (protocolEl) protocolEl.textContent = data.protocol || 'None';
        if (connectedAtEl) {
            const date = new Date(data.created_at);
            connectedAtEl.textContent = date.toLocaleString();
        }
    }

    showLoading(message = 'Loading...') {
        /**
         * Show loading indicator
         */
        const container = document.getElementById(`${this.viewerId}-messages-container`);
        if (!container) return;

        const loadingEl = document.createElement('div');
        loadingEl.id = `${this.viewerId}-loading`;
        loadingEl.className = 'loading-indicator';
        loadingEl.innerHTML = `<span class="loading-spinner"></span> ${message}`;

        container.appendChild(loadingEl);
        container.scrollTop = container.scrollHeight;
    }

    hideLoading() {
        /**
         * Hide loading indicator
         */
        const loadingEl = document.getElementById(`${this.viewerId}-loading`);
        if (loadingEl) {
            loadingEl.remove();
        }
    }

    showError(message) {
        /**
         * Show error message
         */
        this.addSystemMessage(message, 'error');
    }

    close() {
        /**
         * Close the viewer and cleanup
         */
        // Disconnect if connected
        if (this.connected) {
            this.disconnect();
        }

        super.close();
    }
}
