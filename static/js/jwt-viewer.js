/**
 * JWT Viewer JavaScript Component
 * Decodes and displays JSON Web Tokens (JWT)
 *
 * Provides:
 * - JWT token decoding (header, payload, signature)
 * - JSON and Claims Table view modes
 * - Signature verification (optional)
 * - Copy functionality for all sections
 * - Token validation and error handling
 */

class JWTViewer extends BaseViewer {
    constructor(token) {
        const viewerId = `jwt-viewer-${Date.now()}`;
        super(viewerId, 'jwt');

        // Token data
        this.rawToken = token;
        this.header = null;
        this.payload = null;
        this.signature = null;

        // State
        this.isValidJWT = false;
        this.verificationStatus = null;
        this.headerViewMode = 'json'; // 'json' or 'table'
        this.payloadViewMode = 'json'; // 'json' or 'table'
    }

    async open() {
        /**
         * Open the JWT viewer and decode token
         */
        try {
            // Decode JWT
            this.decodeJWT();

            // Create viewer UI
            await this.createViewer();
            this.show();

            // Render decoded data
            this.renderDecodedData();

        } catch (error) {
            console.error('Failed to open JWT viewer:', error);
            this.showError(error.message);
        }
    }

    decodeJWT() {
        /**
         * Decode JWT into header, payload, and signature parts
         */
        try {
            // Remove whitespace
            const token = this.rawToken.trim();

            // Split into three parts
            const parts = token.split('.');
            if (parts.length !== 3) {
                throw new Error('Invalid JWT format. Expected 3 parts separated by dots.');
            }

            // Decode header (first part)
            this.header = this.base64UrlDecode(parts[0]);

            // Decode payload (second part)
            this.payload = this.base64UrlDecode(parts[1]);

            // Store signature (third part - not decoded)
            this.signature = parts[2];

            this.isValidJWT = true;

        } catch (error) {
            console.error('JWT decoding error:', error);
            this.isValidJWT = false;
            throw new Error(`Failed to decode JWT: ${error.message}`);
        }
    }

    base64UrlDecode(base64Url) {
        /**
         * Decode base64url to JSON object
         * Base64url encoding uses - and _ instead of + and /
         */
        try {
            // Convert base64url to base64
            let base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');

            // Pad with = to make length multiple of 4
            const padding = base64.length % 4;
            if (padding > 0) {
                base64 += '='.repeat(4 - padding);
            }

            // Decode base64 to string
            const jsonString = atob(base64);

            // Parse JSON
            return JSON.parse(jsonString);

        } catch (error) {
            throw new Error(`Base64 decode error: ${error.message}`);
        }
    }

    async createViewer() {
        /**
         * Create the JWT viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container jwt-viewer-container" id="${this.viewerId}-container">
                    <!-- Header -->
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">🔑</span>
                            <span>JSON Web Token (JWT)</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>

                    <!-- Body -->
                    <div class="viewer-body jwt-viewer-body">
                        <!-- Encoded Value Section -->
                        <div class="jwt-section">
                            <div class="jwt-section-header">
                                <span class="jwt-section-title">ENCODED VALUE</span>
                                <div class="jwt-section-controls">
                                    <button class="jwt-btn" id="${this.viewerId}-copy-token">COPY</button>
                                    <button class="jwt-btn" id="${this.viewerId}-clear-token">CLEAR</button>
                                </div>
                            </div>
                            <div class="jwt-section-content">
                                <div class="jwt-token-display">
                                    <div class="jwt-token-type">JSON WEB TOKEN (JWT)</div>
                                    <div class="jwt-token-status" id="${this.viewerId}-token-status">
                                        ${this.isValidJWT ? '<span class="jwt-status-valid">Valid JWT</span>' : '<span class="jwt-status-invalid">Invalid JWT</span>'}
                                    </div>
                                    <div class="jwt-token-status" id="${this.viewerId}-signature-status">
                                        ${this.verificationStatus ? '<span class="jwt-status-verified">Signature Verified</span>' : ''}
                                    </div>
                                    <textarea class="jwt-token-input" id="${this.viewerId}-token-input" readonly>${this.rawToken}</textarea>
                                </div>
                            </div>
                        </div>

                        <!-- Decoded Sections -->
                        <div class="jwt-decoded-sections">
                            <!-- Decoded Header -->
                            <div class="jwt-section jwt-decoded-section">
                                <div class="jwt-section-header">
                                    <div class="jwt-section-header-left">
                                        <span class="jwt-section-title">DECODED HEADER</span>
                                        <div class="jwt-tabs">
                                            <button class="jwt-tab active" data-view="json" data-section="header">JSON</button>
                                            <button class="jwt-tab" data-view="table" data-section="header">CLAIMS TABLE</button>
                                        </div>
                                    </div>
                                    <button class="jwt-btn" id="${this.viewerId}-copy-header">COPY</button>
                                </div>
                                <div class="jwt-section-content">
                                    <div class="jwt-decoded-content" id="${this.viewerId}-header-content"></div>
                                </div>
                            </div>

                            <!-- Decoded Payload -->
                            <div class="jwt-section jwt-decoded-section">
                                <div class="jwt-section-header">
                                    <div class="jwt-section-header-left">
                                        <span class="jwt-section-title">DECODED PAYLOAD</span>
                                        <div class="jwt-tabs">
                                            <button class="jwt-tab active" data-view="json" data-section="payload">JSON</button>
                                            <button class="jwt-tab" data-view="table" data-section="payload">CLAIMS TABLE</button>
                                        </div>
                                    </div>
                                    <button class="jwt-btn" id="${this.viewerId}-copy-payload">COPY</button>
                                </div>
                                <div class="jwt-section-content">
                                    <div class="jwt-decoded-content" id="${this.viewerId}-payload-content"></div>
                                </div>
                            </div>

                            <!-- Signature Verification Section (Optional) -->
                            <div class="jwt-section jwt-verify-section">
                            <div class="jwt-section-header">
                                <span class="jwt-section-title">JWT SIGNATURE VERIFICATION (OPTIONAL)</span>
                            </div>
                            <div class="jwt-section-content">
                                <div class="jwt-verify-content">
                                    <p class="jwt-verify-description">Enter the secret used to sign the JWT below:</p>
                                    <div class="jwt-verify-input-group">
                                        <label class="jwt-verify-label">SECRET</label>
                                        <div class="jwt-verify-input-container">
                                            <input type="text" class="jwt-verify-input" id="${this.viewerId}-secret-input" placeholder="a-string-secret-at-least-256-bits-long">
                                            <button class="jwt-btn" id="${this.viewerId}-copy-secret">COPY</button>
                                            <button class="jwt-btn" id="${this.viewerId}-clear-secret">CLEAR</button>
                                        </div>
                                        <div class="jwt-verify-status" id="${this.viewerId}-verify-status"></div>
                                    </div>
                                    <button class="jwt-btn jwt-btn-primary" id="${this.viewerId}-verify-btn">Verify Signature</button>
                                    <div class="jwt-verify-format">
                                        <label>Encoding Format</label>
                                        <select class="jwt-verify-select" id="${this.viewerId}-encoding-format">
                                            <option value="utf8">UTF-8</option>
                                            <option value="base64">Base64</option>
                                            <option value="hex">Hex</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Append to body
        document.body.insertAdjacentHTML('beforeend', viewerHtml);

        // Initialize viewer
        this.init();

        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        /**
         * Setup UI event listeners
         */
        // Copy token button
        const copyTokenBtn = document.getElementById(`${this.viewerId}-copy-token`);
        if (copyTokenBtn) {
            copyTokenBtn.addEventListener('click', () => this.copyToClipboard(this.rawToken, 'Token'));
        }

        // Clear token button
        const clearTokenBtn = document.getElementById(`${this.viewerId}-clear-token`);
        if (clearTokenBtn) {
            clearTokenBtn.addEventListener('click', () => {
                const tokenInput = document.getElementById(`${this.viewerId}-token-input`);
                if (tokenInput) tokenInput.value = '';
            });
        }

        // Copy header button
        const copyHeaderBtn = document.getElementById(`${this.viewerId}-copy-header`);
        if (copyHeaderBtn) {
            copyHeaderBtn.addEventListener('click', () => {
                this.copyToClipboard(JSON.stringify(this.header, null, 2), 'Header');
            });
        }

        // Copy payload button
        const copyPayloadBtn = document.getElementById(`${this.viewerId}-copy-payload`);
        if (copyPayloadBtn) {
            copyPayloadBtn.addEventListener('click', () => {
                this.copyToClipboard(JSON.stringify(this.payload, null, 2), 'Payload');
            });
        }

        // Copy secret button
        const copySecretBtn = document.getElementById(`${this.viewerId}-copy-secret`);
        if (copySecretBtn) {
            copySecretBtn.addEventListener('click', () => {
                const secretInput = document.getElementById(`${this.viewerId}-secret-input`);
                if (secretInput && secretInput.value) {
                    this.copyToClipboard(secretInput.value, 'Secret');
                }
            });
        }

        // Clear secret button
        const clearSecretBtn = document.getElementById(`${this.viewerId}-clear-secret`);
        if (clearSecretBtn) {
            clearSecretBtn.addEventListener('click', () => {
                const secretInput = document.getElementById(`${this.viewerId}-secret-input`);
                const verifyStatus = document.getElementById(`${this.viewerId}-verify-status`);
                if (secretInput) secretInput.value = '';
                if (verifyStatus) verifyStatus.innerHTML = '';
            });
        }

        // Verify signature button
        const verifyBtn = document.getElementById(`${this.viewerId}-verify-btn`);
        if (verifyBtn) {
            verifyBtn.addEventListener('click', () => this.verifySignature());
        }

        // Tab switching for header and payload
        const tabs = this.container.querySelectorAll('.jwt-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const view = e.target.dataset.view;
                const section = e.target.dataset.section;
                this.switchView(section, view);
            });
        });
    }

    renderDecodedData() {
        /**
         * Render decoded header and payload
         */
        this.renderSection('header', this.header);
        this.renderSection('payload', this.payload);
    }

    renderSection(section, data) {
        /**
         * Render a section (header or payload) in JSON view
         */
        const contentEl = document.getElementById(`${this.viewerId}-${section}-content`);
        if (!contentEl) return;

        const viewMode = section === 'header' ? this.headerViewMode : this.payloadViewMode;

        if (viewMode === 'json') {
            contentEl.innerHTML = `<pre class="jwt-json">${this.syntaxHighlight(data)}</pre>`;
        } else {
            contentEl.innerHTML = this.renderTable(data);
        }
    }

    renderTable(data) {
        /**
         * Render data as a claims table
         */
        let html = '<table class="jwt-claims-table">';
        html += '<thead><tr><th>Claim</th><th>Value</th></tr></thead>';
        html += '<tbody>';

        for (const [key, value] of Object.entries(data)) {
            let displayValue = value;

            // Format special claims
            if (key === 'iat' || key === 'exp' || key === 'nbf') {
                // Unix timestamp - convert to readable date
                const date = new Date(value * 1000);
                displayValue = `${value} (${date.toISOString()})`;
            } else if (typeof value === 'object') {
                displayValue = JSON.stringify(value);
            }

            html += `<tr><td class="jwt-claim-key">"${this.escapeHtml(key)}"</td><td class="jwt-claim-value">${this.escapeHtml(String(displayValue))}</td></tr>`;
        }

        html += '</tbody></table>';
        return html;
    }

    syntaxHighlight(obj) {
        /**
         * Syntax highlight JSON object
         */
        let json = JSON.stringify(obj, null, 2);
        json = this.escapeHtml(json);

        // Colorize
        json = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?)/g, (match) => {
            let cls = 'jwt-json-string';
            if (/:$/.test(match)) {
                cls = 'jwt-json-key';
            }
            return `<span class="${cls}">${match}</span>`;
        });

        json = json.replace(/\b(true|false)\b/g, '<span class="jwt-json-boolean">$1</span>');
        json = json.replace(/\b(-?\d+)\b/g, '<span class="jwt-json-number">$1</span>');
        json = json.replace(/\bnull\b/g, '<span class="jwt-json-null">null</span>');

        return json;
    }

    switchView(section, view) {
        /**
         * Switch between JSON and table view for a section
         */
        // Update state
        if (section === 'header') {
            this.headerViewMode = view;
        } else {
            this.payloadViewMode = view;
        }

        // Update tab active state
        const tabs = this.container.querySelectorAll(`.jwt-tab[data-section="${section}"]`);
        tabs.forEach(tab => {
            if (tab.dataset.view === view) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Re-render section
        const data = section === 'header' ? this.header : this.payload;
        this.renderSection(section, data);
    }

    async verifySignature() {
        /**
         * Verify JWT signature using the provided secret
         */
        const secretInput = document.getElementById(`${this.viewerId}-secret-input`);
        const verifyStatus = document.getElementById(`${this.viewerId}-verify-status`);
        const encodingFormat = document.getElementById(`${this.viewerId}-encoding-format`);
        const signatureStatus = document.getElementById(`${this.viewerId}-signature-status`);

        if (!secretInput || !verifyStatus) return;

        const secret = secretInput.value.trim();
        if (!secret) {
            verifyStatus.innerHTML = '<span class="jwt-status-error">⚠ Please enter a secret</span>';
            return;
        }

        verifyStatus.innerHTML = '<span class="jwt-status-pending">⏳ Verifying...</span>';

        try {
            // Call backend API to verify signature
            const response = await fetch('/api/jwt/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: this.rawToken,
                    secret: secret,
                    encoding: encodingFormat ? encodingFormat.value : 'utf8'
                })
            });

            const result = await response.json();

            if (response.ok && result.verified) {
                verifyStatus.innerHTML = '<span class="jwt-status-verified">✓ Valid secret</span>';
                signatureStatus.innerHTML = '<span class="jwt-status-verified">Signature Verified</span>';
                this.verificationStatus = true;
            } else {
                verifyStatus.innerHTML = `<span class="jwt-status-error">✗ ${result.error || 'Invalid signature'}</span>`;
                signatureStatus.innerHTML = '';
                this.verificationStatus = false;
            }

        } catch (error) {
            console.error('Verification error:', error);
            verifyStatus.innerHTML = '<span class="jwt-status-error">✗ Verification failed</span>';
            signatureStatus.innerHTML = '';
            this.verificationStatus = false;
        }
    }

    copyToClipboard(text, label) {
        /**
         * Copy text to clipboard with user feedback
         */
        navigator.clipboard.writeText(text).then(() => {
            console.log(`${label} copied to clipboard`);
            // You could add a toast notification here
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }

    escapeHtml(text) {
        /**
         * Escape HTML special characters
         */
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showError(message) {
        /**
         * Display error message in viewer
         */
        const errorHtml = `
            <div class="viewer-overlay visible" id="${this.viewerId}-overlay">
                <div class="viewer-container jwt-viewer-container" id="${this.viewerId}-container">
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">⚠️</span>
                            <span>JWT Decode Error</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>
                    <div class="viewer-body">
                        <div class="viewer-error">
                            <div class="viewer-error-message">${this.escapeHtml(message)}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', errorHtml);
        this.init();
    }
}

// Export to window object for use by terminal.js
window.JWTViewer = JWTViewer;
