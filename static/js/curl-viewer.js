/**
 * HTTP Request Viewer (CurlViewer)
 *
 * Provides interactive interface for:
 * - Executing HTTP requests (GET, POST, PUT, DELETE, etc.)
 * - Viewing response with syntax highlighting
 * - Timing breakdown visualization
 * - Environment variable management
 * - Request history (localStorage)
 * - Export as curl/python/javascript
 */

class CurlViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `curl-viewer-${Date.now()}`;
        super(viewerId, 'curl');

        this.url = params.url || '';
        this.method = params.method || 'GET';
        this.headers = params.headers || {};
        this.body = params.body || '';
        this.authType = params.auth_type || 'none';
        this.authCredentials = params.auth_credentials || '';

        this.baseUrl = '/http';
        this.history = this.loadHistory();
        this.environment = this.loadEnvironment();
    }

    async open() {
        /**
         * Open the HTTP viewer
         */
        try {
            // Create viewer UI
            await this.createViewer();
            super.init();
            this.show();

            // Populate form with initial data if provided
            if (this.url) {
                this.populateForm();
            }

            // Attach event listeners
            this.attachEventListeners();
            this.loadHistoryUI();
            this.loadEnvironmentUI();

        } catch (error) {
            console.error('Failed to open HTTP viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the HTTP viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container curl-viewer-container" id="${this.viewerId}-container">
                    <div class="curl-viewer">
                        <!-- Main content will go here -->
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
            <div class="viewer-layout">
                ${this.getRequestPanel()}
                ${this.getResponsePanel()}
            </div>
        `;
    }

    getRequestPanel() {
        return `
            <div class="request-panel">
                <div class="panel-header">
                    <h3>Request</h3>
                    <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                </div>
                <div class="request-form">
                    ${this.getRequestForm()}
                </div>
            </div>
        `;
    }

    getRequestForm() {
        return `
            <div class="form-row">
                <select id="${this.viewerId}-http-method" class="http-method-select">
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                    <option value="PATCH">PATCH</option>
                    <option value="HEAD">HEAD</option>
                    <option value="OPTIONS">OPTIONS</option>
                </select>
                <input type="text" id="${this.viewerId}-http-url" class="http-url-input" placeholder="https://api.example.com/endpoint" value="${this.escapeHtml(this.url)}">
                <button id="${this.viewerId}-execute-request" class="btn-primary">Send</button>
            </div>

            <div class="request-tabs">
                <button class="tab-btn active" data-tab="headers">Headers</button>
                <button class="tab-btn" data-tab="body">Body</button>
                <button class="tab-btn" data-tab="auth">Auth</button>
                <button class="tab-btn" data-tab="options">Options</button>
            </div>

            <div class="tab-content active" data-tab-content="headers">
                <label for="${this.viewerId}-http-headers">Headers (one per line: Key: Value)</label>
                <textarea id="${this.viewerId}-http-headers" rows="6" placeholder="Content-Type: application/json&#10;Accept: application/json"></textarea>
            </div>

            <div class="tab-content" data-tab-content="body">
                <label for="${this.viewerId}-http-body">Request Body</label>
                <textarea id="${this.viewerId}-http-body" rows="10" placeholder='{"key": "value"}'></textarea>
            </div>

            <div class="tab-content" data-tab-content="auth">
                <div class="form-group">
                    <label for="${this.viewerId}-auth-type">Authentication Type</label>
                    <select id="${this.viewerId}-auth-type">
                        <option value="none">None</option>
                        <option value="basic">Basic Auth</option>
                        <option value="bearer">Bearer Token</option>
                        <option value="api_key">API Key</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="${this.viewerId}-auth-credentials">Credentials</label>
                    <input type="text" id="${this.viewerId}-auth-credentials" placeholder="username:password or token">
                </div>
            </div>

            <div class="tab-content" data-tab-content="options">
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="${this.viewerId}-follow-redirects" checked>
                        Follow Redirects
                    </label>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="${this.viewerId}-verify-ssl" checked>
                        Verify SSL Certificates
                    </label>
                </div>
                <div class="form-group">
                    <label for="${this.viewerId}-timeout">Timeout (seconds)</label>
                    <input type="number" id="${this.viewerId}-timeout" value="30" min="1" max="300">
                </div>
            </div>

            <div class="export-actions">
                <button id="${this.viewerId}-export-curl" class="btn-secondary">Export as curl</button>
                <button id="${this.viewerId}-export-python" class="btn-secondary">Export as Python</button>
                <button id="${this.viewerId}-export-javascript" class="btn-secondary">Export as JavaScript</button>
            </div>
        `;
    }

    getResponsePanel() {
        return `
            <div class="response-panel">
                <div class="response-tabs">
                    <button class="tab-btn active" data-tab="response">Response</button>
                    <button class="tab-btn" data-tab="history">History</button>
                    <button class="tab-btn" data-tab="environment">Environment</button>
                </div>

                <div class="tab-content active" data-tab-content="response">
                    <div id="${this.viewerId}-response-container" class="response-container">
                        <p class="empty-state">Execute a request to see the response</p>
                    </div>
                </div>

                <div class="tab-content" data-tab-content="history">
                    <div class="history-header">
                        <h4>Request History</h4>
                        <button id="${this.viewerId}-clear-history" class="btn-danger-small">Clear All</button>
                    </div>
                    <div id="${this.viewerId}-request-history" class="request-history">
                        <p class="empty-state">No request history</p>
                    </div>
                </div>

                <div class="tab-content" data-tab-content="environment">
                    <div class="environment-section">
                        <h4>Environment Variables</h4>
                        <p class="help-text">Use {{VARIABLE_NAME}} in URL, headers, or body to substitute values</p>

                        <div class="add-env-var">
                            <input type="text" id="${this.viewerId}-env-var-name" placeholder="VARIABLE_NAME" pattern="[A-Z_][A-Z0-9_]*">
                            <input type="text" id="${this.viewerId}-env-var-value" placeholder="value">
                            <button id="${this.viewerId}-add-env-var" class="btn-primary">Add</button>
                        </div>

                        <div id="${this.viewerId}-environment-variables" class="environment-variables">
                            <p class="empty-state">No environment variables</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    populateForm() {
        /**
         * Populate form with initial data
         */
        // Set URL
        const urlInput = document.getElementById(`${this.viewerId}-http-url`);
        if (urlInput && this.url) {
            urlInput.value = this.url;
        }

        // Set method
        const methodSelect = document.getElementById(`${this.viewerId}-http-method`);
        if (methodSelect && this.method) {
            methodSelect.value = this.method.toUpperCase();
        }

        // Set body
        const bodyInput = document.getElementById(`${this.viewerId}-http-body`);
        if (bodyInput && this.body) {
            bodyInput.value = this.body;
        }

        // Set headers
        if (this.headers && Object.keys(this.headers).length > 0) {
            const headersInput = document.getElementById(`${this.viewerId}-http-headers`);
            if (headersInput) {
                headersInput.value = this.formatHeadersForInput(this.headers);
            }
        }
    }

    attachEventListeners() {
        // Execute request button
        const executeBtn = document.getElementById(`${this.viewerId}-execute-request`);
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.executeRequest());
        }

        // Export buttons
        const exportCurlBtn = document.getElementById(`${this.viewerId}-export-curl`);
        if (exportCurlBtn) {
            exportCurlBtn.addEventListener('click', () => this.exportAsCode('curl'));
        }

        const exportPythonBtn = document.getElementById(`${this.viewerId}-export-python`);
        if (exportPythonBtn) {
            exportPythonBtn.addEventListener('click', () => this.exportAsCode('python'));
        }

        const exportJsBtn = document.getElementById(`${this.viewerId}-export-javascript`);
        if (exportJsBtn) {
            exportJsBtn.addEventListener('click', () => this.exportAsCode('javascript'));
        }

        // Environment variable management
        const addEnvBtn = document.getElementById(`${this.viewerId}-add-env-var`);
        if (addEnvBtn) {
            addEnvBtn.addEventListener('click', () => this.addEnvironmentVariable());
        }

        // Clear history button
        const clearHistoryBtn = document.getElementById(`${this.viewerId}-clear-history`);
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        }

        // Close button
        const closeBtn = this.container.querySelector('.viewer-btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Tab switching for request form
        const requestTabs = this.container.querySelectorAll('.request-tabs .tab-btn');
        requestTabs.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;

                // Update active button
                requestTabs.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Update active content
                const contents = this.container.querySelectorAll('.request-form .tab-content');
                contents.forEach(content => {
                    if (content.dataset.tabContent === tabName) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });

        // Tab switching for response panel
        const responseTabs = this.container.querySelectorAll('.response-tabs .tab-btn');
        responseTabs.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabName = btn.dataset.tab;

                // Update active button
                responseTabs.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Update active content
                const contents = this.container.querySelectorAll('.response-panel > .tab-content');
                contents.forEach(content => {
                    if (content.dataset.tabContent === tabName) {
                        content.classList.add('active');
                    } else {
                        content.classList.remove('active');
                    }
                });
            });
        });

        // History item click
        this.container.addEventListener('click', (e) => {
            if (e.target.closest('.history-item')) {
                const index = e.target.closest('.history-item').dataset.index;
                this.loadFromHistory(parseInt(index));
            }
        });
    }

    async executeRequest() {
        try {
            // Get request data from form
            const method = document.getElementById(`${this.viewerId}-http-method`)?.value || 'GET';
            const url = document.getElementById(`${this.viewerId}-http-url`)?.value;
            const body = document.getElementById(`${this.viewerId}-http-body`)?.value || '';
            const authType = document.getElementById(`${this.viewerId}-auth-type`)?.value || 'none';
            const authCreds = document.getElementById(`${this.viewerId}-auth-credentials`)?.value || '';
            const followRedirects = document.getElementById(`${this.viewerId}-follow-redirects`)?.checked ?? true;
            const verifySsl = document.getElementById(`${this.viewerId}-verify-ssl`)?.checked ?? true;
            const timeout = parseInt(document.getElementById(`${this.viewerId}-timeout`)?.value || '30');

            if (!url) {
                this.showError('URL is required');
                return;
            }

            // Parse headers
            const headersText = document.getElementById(`${this.viewerId}-http-headers`)?.value || '';
            const headers = this.parseHeaders(headersText);

            // Show loading state
            this.showLoading();

            // Build request
            const requestData = {
                method: method.toUpperCase(),
                url: url,
                headers: headers,
                body: body || null,
                auth_type: authType,
                auth_credentials: authCreds || null,
                follow_redirects: followRedirects,
                timeout_seconds: timeout,
                verify_ssl: verifySsl,
                environment: this.environment
            };

            // Execute request
            const response = await fetch(`${this.baseUrl}/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }

            const result = await response.json();

            // Display response
            this.displayResponse(result);

            // Save to history
            this.addToHistory(requestData, result);

        } catch (error) {
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayResponse(response) {
        const responseContainer = document.getElementById(`${this.viewerId}-response-container`);
        if (!responseContainer) return;

        // Status code with color coding
        const statusClass = this.getStatusClass(response.status_code);

        let html = `
            <div class="response-section">
                <div class="response-status ${statusClass}">
                    <span class="status-code">${response.status_code}</span>
                    <span class="status-text">${this.getStatusText(response.status_code)}</span>
                </div>

                <div class="response-timing">
                    <strong>Total Time:</strong> ${this.formatTiming(response.timing.total_ms)}
                </div>

                ${this.renderTimingBreakdown(response.timing)}

                ${response.redirect_chain && response.redirect_chain.length > 0 ?
                    this.renderRedirectChain(response.redirect_chain) : ''}

                <div class="response-headers">
                    <h4>Response Headers</h4>
                    <pre><code class="language-http">${this.formatHeaders(response.headers)}</code></pre>
                </div>

                <div class="response-body">
                    <h4>Response Body</h4>
                    ${this.renderResponseBody(response.body, response.headers)}
                </div>
            </div>
        `;

        responseContainer.innerHTML = html;

        // Apply syntax highlighting if Prism is available
        if (window.Prism) {
            Prism.highlightAllUnder(responseContainer);
        }
    }

    renderTimingBreakdown(timing) {
        if (timing.total_ms === 0) return '';

        return `
            <div class="timing-breakdown">
                <h4>Timing Breakdown</h4>
                <div class="timing-bars">
                    ${timing.dns_lookup_ms > 0 ? `<div class="timing-bar" style="width: ${(timing.dns_lookup_ms / timing.total_ms) * 100}%">DNS: ${timing.dns_lookup_ms.toFixed(0)}ms</div>` : ''}
                    ${timing.tcp_connect_ms > 0 ? `<div class="timing-bar" style="width: ${(timing.tcp_connect_ms / timing.total_ms) * 100}%">TCP: ${timing.tcp_connect_ms.toFixed(0)}ms</div>` : ''}
                    ${timing.tls_handshake_ms > 0 ? `<div class="timing-bar" style="width: ${(timing.tls_handshake_ms / timing.total_ms) * 100}%">TLS: ${timing.tls_handshake_ms.toFixed(0)}ms</div>` : ''}
                    ${timing.server_processing_ms > 0 ? `<div class="timing-bar" style="width: ${(timing.server_processing_ms / timing.total_ms) * 100}%">Server: ${timing.server_processing_ms.toFixed(0)}ms</div>` : ''}
                    ${timing.transfer_ms > 0 ? `<div class="timing-bar" style="width: ${(timing.transfer_ms / timing.total_ms) * 100}%">Transfer: ${timing.transfer_ms.toFixed(0)}ms</div>` : ''}
                    <div class="timing-total">Total: ${timing.total_ms.toFixed(0)}ms</div>
                </div>
            </div>
        `;
    }

    renderRedirectChain(chain) {
        return `
            <div class="redirect-chain">
                <h4>Redirect Chain</h4>
                <ol>
                    ${chain.map(url => `<li>${this.escapeHtml(url)}</li>`).join('')}
                </ol>
            </div>
        `;
    }

    renderResponseBody(body, headers) {
        const contentType = headers['content-type'] || headers['Content-Type'] || '';

        if (contentType.includes('application/json')) {
            try {
                const formatted = JSON.stringify(JSON.parse(body), null, 2);
                return `<pre><code class="language-json">${this.escapeHtml(formatted)}</code></pre>`;
            } catch {
                return `<pre><code>${this.escapeHtml(body)}</code></pre>`;
            }
        } else if (contentType.includes('text/html')) {
            return `<pre><code class="language-html">${this.escapeHtml(body)}</code></pre>`;
        } else if (contentType.includes('text/xml') || contentType.includes('application/xml')) {
            return `<pre><code class="language-xml">${this.escapeHtml(body)}</code></pre>`;
        } else {
            return `<pre><code>${this.escapeHtml(body)}</code></pre>`;
        }
    }

    async exportAsCode(language) {
        try {
            // Get current request data
            const method = document.getElementById(`${this.viewerId}-http-method`)?.value || 'GET';
            const url = document.getElementById(`${this.viewerId}-http-url`)?.value;
            const body = document.getElementById(`${this.viewerId}-http-body`)?.value || '';
            const headersText = document.getElementById(`${this.viewerId}-http-headers`)?.value || '';
            const headers = this.parseHeaders(headersText);

            if (!url) {
                this.showError('URL is required for export');
                return;
            }

            const requestData = {
                method: method.toUpperCase(),
                url: url,
                headers: headers,
                body: body || null,
                auth_type: 'none',
                auth_credentials: null,
                follow_redirects: true,
                timeout_seconds: 30,
                verify_ssl: true,
                environment: {}
            };

            const response = await fetch(`${this.baseUrl}/export`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ request: requestData, language: language })
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            const result = await response.json();
            this.showExportModal(result.code, result.language);

        } catch (error) {
            this.showError(error.message);
        }
    }

    showExportModal(code, language) {
        // Create modal or display in a textarea
        const modal = document.createElement('div');
        modal.className = 'export-modal';
        modal.innerHTML = `
            <div class="export-modal-content">
                <h3>Export as ${language}</h3>
                <textarea readonly style="width: 100%; height: 300px; font-family: monospace;">${code}</textarea>
                <div class="export-modal-actions">
                    <button onclick="navigator.clipboard.writeText(\`${code.replace(/`/g, '\\`')}\`)">Copy to Clipboard</button>
                    <button onclick="this.closest('.export-modal').remove()">Close</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    addEnvironmentVariable() {
        const name = document.getElementById(`${this.viewerId}-env-var-name`)?.value;
        const value = document.getElementById(`${this.viewerId}-env-var-value`)?.value;

        if (!name || !value) {
            this.showError('Variable name and value are required');
            return;
        }

        // Validate name format
        if (!/^[A-Z_][A-Z0-9_]*$/.test(name)) {
            this.showError('Variable name must be UPPERCASE_WITH_UNDERSCORES');
            return;
        }

        this.environment[name] = value;
        this.saveEnvironment();
        this.loadEnvironmentUI();

        // Clear inputs
        const nameInput = document.getElementById(`${this.viewerId}-env-var-name`);
        const valueInput = document.getElementById(`${this.viewerId}-env-var-value`);
        if (nameInput) nameInput.value = '';
        if (valueInput) valueInput.value = '';
    }

    loadEnvironmentUI() {
        const envList = document.getElementById(`${this.viewerId}-environment-variables`);
        if (!envList) return;

        if (Object.keys(this.environment).length === 0) {
            envList.innerHTML = '<p class="empty-state">No environment variables</p>';
            return;
        }

        let html = '<ul class="env-var-list">';
        for (const [name, value] of Object.entries(this.environment)) {
            html += `
                <li class="env-var-item">
                    <span class="env-var-name">${this.escapeHtml(name)}</span>:
                    <span class="env-var-value">${this.escapeHtml(value)}</span>
                    <button class="remove-env-var" data-name="${this.escapeHtml(name)}">Remove</button>
                </li>
            `;
        }
        html += '</ul>';
        envList.innerHTML = html;

        // Attach remove handlers
        envList.querySelectorAll('.remove-env-var').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const name = e.target.dataset.name;
                delete this.environment[name];
                this.saveEnvironment();
                this.loadEnvironmentUI();
            });
        });
    }

    addToHistory(request, response) {
        const historyEntry = {
            request: request,
            response: response,
            timestamp: new Date().toISOString(),
            success: true
        };

        this.history.unshift(historyEntry);

        // Keep only last 50 entries
        if (this.history.length > 50) {
            this.history = this.history.slice(0, 50);
        }

        this.saveHistory();
        this.loadHistoryUI();
    }

    loadHistoryUI() {
        const historyList = document.getElementById(`${this.viewerId}-request-history`);
        if (!historyList) return;

        if (this.history.length === 0) {
            historyList.innerHTML = '<p class="empty-state">No request history</p>';
            return;
        }

        let html = '<ul class="history-list">';
        this.history.forEach((entry, index) => {
            const timestamp = new Date(entry.timestamp).toLocaleString();
            const statusClass = this.getStatusClass(entry.response.status_code);
            html += `
                <li class="history-item ${statusClass}" data-index="${index}">
                    <span class="history-method">${entry.request.method}</span>
                    <span class="history-url">${this.escapeHtml(entry.request.url)}</span>
                    <span class="history-status">${entry.response.status_code}</span>
                    <span class="history-time">${timestamp}</span>
                </li>
            `;
        });
        html += '</ul>';
        historyList.innerHTML = html;
    }

    loadFromHistory(index) {
        const entry = this.history[index];
        if (!entry) return;

        // Populate form with historical request
        const methodInput = document.getElementById(`${this.viewerId}-http-method`);
        if (methodInput) methodInput.value = entry.request.method;

        const urlInput = document.getElementById(`${this.viewerId}-http-url`);
        if (urlInput) urlInput.value = entry.request.url;

        const bodyInput = document.getElementById(`${this.viewerId}-http-body`);
        if (bodyInput) bodyInput.value = entry.request.body || '';

        const headersInput = document.getElementById(`${this.viewerId}-http-headers`);
        if (headersInput) headersInput.value = this.formatHeadersForInput(entry.request.headers);

        // Display response
        this.displayResponse(entry.response);
    }

    clearHistory() {
        if (confirm('Clear all request history?')) {
            this.history = [];
            this.saveHistory();
            this.loadHistoryUI();
        }
    }

    // Utility methods
    parseHeaders(headersText) {
        const headers = {};
        headersText.split('\n').forEach(line => {
            const colonIndex = line.indexOf(':');
            if (colonIndex > 0) {
                const key = line.substring(0, colonIndex).trim();
                const value = line.substring(colonIndex + 1).trim();
                if (key && value) {
                    headers[key] = value;
                }
            }
        });
        return headers;
    }

    formatHeaders(headers) {
        return Object.entries(headers)
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n');
    }

    formatHeadersForInput(headers) {
        return Object.entries(headers)
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n');
    }

    getStatusClass(statusCode) {
        if (statusCode >= 200 && statusCode < 300) return 'status-success';
        if (statusCode >= 300 && statusCode < 400) return 'status-redirect';
        if (statusCode >= 400 && statusCode < 500) return 'status-client-error';
        if (statusCode >= 500) return 'status-server-error';
        return 'status-unknown';
    }

    getStatusText(statusCode) {
        const statusTexts = {
            200: 'OK', 201: 'Created', 204: 'No Content',
            301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
            400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found',
            500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable'
        };
        return statusTexts[statusCode] || 'Unknown';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatTiming(ms) {
        if (ms < 1000) {
            return `${Math.round(ms)}ms`;
        } else {
            return `${(ms / 1000).toFixed(2)}s`;
        }
    }

    showLoading() {
        const responseContainer = document.getElementById(`${this.viewerId}-response-container`);
        if (responseContainer) {
            responseContainer.innerHTML = '<div class="loading">Executing request...</div>';
        }
    }

    hideLoading() {
        // Loading state cleared by displayResponse or showError
    }

    showError(message) {
        const responseContainer = document.getElementById(`${this.viewerId}-response-container`);
        if (responseContainer) {
            responseContainer.innerHTML = `<div class="error">Error: ${this.escapeHtml(message)}</div>`;
        }
    }

    // LocalStorage methods
    loadHistory() {
        try {
            const stored = localStorage.getItem('curlcat_history');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }

    saveHistory() {
        try {
            localStorage.setItem('curlcat_history', JSON.stringify(this.history));
        } catch (error) {
            console.error('Failed to save history:', error);
        }
    }

    loadEnvironment() {
        try {
            const stored = localStorage.getItem('curlcat_environment');
            return stored ? JSON.parse(stored) : {};
        } catch {
            return {};
        }
    }

    saveEnvironment() {
        try {
            localStorage.setItem('curlcat_environment', JSON.stringify(this.environment));
        } catch (error) {
            console.error('Failed to save environment:', error);
        }
    }
}

// Export CurlViewer for use by terminal.js
window.CurlViewer = CurlViewer;
