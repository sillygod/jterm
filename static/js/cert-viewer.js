/**
 * Certificate Viewer JavaScript Component
 * T025: CertViewer class for interactive certificate inspection
 *
 * Provides:
 * - Certificate details display
 * - Certificate chain visualization
 * - Certificate comparison
 * - Export functionality (PEM, DER, text)
 * - Trust status and expiry warnings
 */

class CertViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `cert-viewer-${Date.now()}`;
        super(viewerId, 'cert');

        // Parse source (URL or file path)
        this.source = params.source || params.url || params.file_path;
        this.port = params.port || 443;
        this.includeChain = params.includeChain !== false;

        // State
        this.certificate = null;
        this.chain = null;
        this.warnings = [];
        this.selectedCert = null; // For chain navigation
        this.useD3Tree = false; // Toggle for D3 tree visualization
        this.d3Loaded = false; // Track if D3 is loaded
    }

    async open() {
        /**
         * Open the certificate viewer and load certificate data
         */
        try {
            // Create viewer UI
            await this.createViewer();
            this.show();

            // Load certificate
            await this.loadCertificate();

            // Render certificate details
            this.renderCertificate();

            // Render chain visualization if available
            if (this.chain) {
                this.renderChainVisualization();
            }

        } catch (error) {
            console.error('Failed to open certificate viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the certificate viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container cert-viewer-container" id="${this.viewerId}-container">
                    <!-- Header -->
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">🔒</span>
                            <span>Certificate Inspector</span>
                            <span class="viewer-subtitle">${this.getSourceName()}</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn" id="${this.viewerId}-export-btn" title="Export certificate">
                                Export
                            </button>
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>

                    <!-- Body with split view -->
                    <div class="viewer-body">
                        <div class="viewer-split cert-viewer-split">
                            <!-- Left panel: Certificate chain visualization -->
                            <div class="viewer-panel cert-chain-panel">
                                <div class="viewer-panel-header">Certificate Chain</div>
                                <div class="viewer-panel-content">
                                    <div id="${this.viewerId}-chain-viz" class="cert-chain-visualization">
                                        <div class="viewer-loading">
                                            <div class="viewer-spinner"></div>
                                            <div>Loading certificate...</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Right panel: Certificate details -->
                            <div class="viewer-panel cert-detail-panel">
                                <div class="viewer-panel-header">Certificate Details</div>
                                <div class="viewer-panel-content">
                                    <div id="${this.viewerId}-cert-detail" class="cert-detail">
                                        <div class="viewer-empty">
                                            <div class="viewer-empty-message">Loading certificate details...</div>
                                        </div>
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
        // Export button
        const exportBtn = document.getElementById(`${this.viewerId}-export-btn`);
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.showExportDialog());
        }
    }

    async loadCertificate() {
        /**
         * Fetch certificate from API
         */
        try {
            const response = await fetch('/api/certificates/fetch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: this.source,  // Backend expects 'url' not 'source'
                    port: this.port,
                    timeout: 10  // Add timeout parameter
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to fetch certificate');
            }

            const data = await response.json();
            this.certificate = data.certificate;
            this.chain = data.chain;
            this.warnings = data.warnings || [];

            // Initially select leaf certificate
            this.selectedCert = this.certificate;

        } catch (error) {
            console.error('Failed to load certificate:', error);
            throw error;
        }
    }

    renderCertificate() {
        /**
         * Render certificate details in the right panel
         */
        const detailPanel = document.getElementById(`${this.viewerId}-cert-detail`);
        if (!detailPanel) return;

        const cert = this.selectedCert || this.certificate;
        if (!cert) {
            detailPanel.innerHTML = '<div class="viewer-empty-message">No certificate selected</div>';
            return;
        }

        // Build warnings section
        let warningsHtml = '';
        if (this.warnings.length > 0) {
            warningsHtml = `
                <div class="cert-warnings">
                    ${this.warnings.map(w => `
                        <div class="cert-warning cert-warning-${w.severity}">
                            <span class="cert-warning-icon">${w.severity === 'error' ? '⚠️' : '⚡'}</span>
                            <span class="cert-warning-message">${this.escapeHtml(w.message)}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        // Build certificate details
        const detailHtml = `
            ${warningsHtml}

            <div class="cert-section">
                <div class="cert-section-header">Subject Information</div>
                <div class="cert-field">
                    <span class="cert-field-label">Common Name:</span>
                    <span class="cert-field-value">${this.escapeHtml(cert.display_name || cert.subject)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Subject:</span>
                    <span class="cert-field-value cert-field-mono">${this.escapeHtml(cert.subject)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Serial Number:</span>
                    <span class="cert-field-value cert-field-mono">${this.escapeHtml(cert.serial_number)}</span>
                </div>
            </div>

            <div class="cert-section">
                <div class="cert-section-header">Issuer Information</div>
                <div class="cert-field">
                    <span class="cert-field-label">Issuer:</span>
                    <span class="cert-field-value cert-field-mono">${this.escapeHtml(cert.issuer)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Self-Signed:</span>
                    <span class="cert-field-value">${cert.is_self_signed ? 'Yes' : 'No'}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Certificate Authority:</span>
                    <span class="cert-field-value">${cert.is_ca ? 'Yes' : 'No'}</span>
                </div>
            </div>

            <div class="cert-section">
                <div class="cert-section-header">Validity</div>
                <div class="cert-field">
                    <span class="cert-field-label">Valid From:</span>
                    <span class="cert-field-value">${this.formatDate(cert.not_before)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Valid Until:</span>
                    <span class="cert-field-value ${cert.is_expired ? 'cert-expired' : ''}">${this.formatDate(cert.not_after)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Days Until Expiry:</span>
                    <span class="cert-field-value ${cert.is_expiring_soon ? 'cert-warning-text' : ''}">${cert.days_until_expiry} days</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">Status:</span>
                    <span class="cert-field-value">
                        <span class="cert-status cert-status-${cert.trust_status}">${this.formatTrustStatus(cert.trust_status)}</span>
                    </span>
                </div>
            </div>

            <div class="cert-section">
                <div class="cert-section-header">Public Key</div>
                <div class="cert-field">
                    <span class="cert-field-label">Algorithm:</span>
                    <span class="cert-field-value">${this.escapeHtml(cert.public_key.display_algorithm)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">SHA-256 Fingerprint:</span>
                    <span class="cert-field-value cert-field-mono cert-fingerprint">${this.escapeHtml(cert.public_key.fingerprint_sha256)}</span>
                </div>
                <div class="cert-field">
                    <span class="cert-field-label">SHA-1 Fingerprint:</span>
                    <span class="cert-field-value cert-field-mono cert-fingerprint">${this.escapeHtml(cert.public_key.fingerprint_sha1)}</span>
                </div>
            </div>

            ${cert.san && cert.san.length > 0 ? `
                <div class="cert-section">
                    <div class="cert-section-header">Subject Alternative Names (${cert.san.length})</div>
                    <div class="cert-san-list">
                        ${cert.san.map(san => `<div class="cert-san-item">${this.escapeHtml(san)}</div>`).join('')}
                    </div>
                </div>
            ` : ''}

            ${cert.key_usage && cert.key_usage.length > 0 ? `
                <div class="cert-section">
                    <div class="cert-section-header">Key Usage</div>
                    <div class="cert-usage-list">
                        ${cert.key_usage.map(usage => `<div class="cert-usage-item">${this.escapeHtml(usage)}</div>`).join('')}
                    </div>
                </div>
            ` : ''}

            ${cert.extended_key_usage && cert.extended_key_usage.length > 0 ? `
                <div class="cert-section">
                    <div class="cert-section-header">Extended Key Usage</div>
                    <div class="cert-usage-list">
                        ${cert.extended_key_usage.map(usage => `<div class="cert-usage-item">${this.escapeHtml(usage)}</div>`).join('')}
                    </div>
                </div>
            ` : ''}
        `;

        detailPanel.innerHTML = detailHtml;
    }

    renderChainVisualization() {
        /**
         * Render certificate chain tree visualization
         * This will be enhanced with D3.js in T029
         */
        const chainViz = document.getElementById(`${this.viewerId}-chain-viz`);
        if (!chainViz) return;

        if (!this.chain) {
            chainViz.innerHTML = `
                <div class="cert-chain-simple">
                    <div class="cert-chain-item cert-chain-item-single" onclick="window.certViewers['${this.viewerId}'].selectCertificate(null)">
                        <div class="cert-chain-icon">📜</div>
                        <div class="cert-chain-label">${this.escapeHtml(this.certificate.display_name)}</div>
                        <div class="cert-chain-type">Single Certificate</div>
                    </div>
                </div>
            `;
            return;
        }

        // Build simple chain visualization (will be replaced with D3 tree)
        const certs = [];

        // Add leaf
        certs.push({
            cert: this.chain.leaf,
            type: 'Leaf Certificate',
            icon: '🌐'
        });

        // Add intermediates
        if (this.chain.intermediates) {
            this.chain.intermediates.forEach(inter => {
                certs.push({
                    cert: inter,
                    type: 'Intermediate CA',
                    icon: '🔗'
                });
            });
        }

        // Add root
        if (this.chain.root) {
            certs.push({
                cert: this.chain.root,
                type: 'Root CA',
                icon: '🏛️'
            });
        }

        const chainHtml = `
            <div class="cert-chain-simple">
                ${certs.map((item, index) => `
                    <div class="cert-chain-item ${this.selectedCert === item.cert ? 'cert-chain-item-selected' : ''}"
                         onclick="window.certViewers['${this.viewerId}'].selectCertificate(${index})">
                        <div class="cert-chain-icon">${item.icon}</div>
                        <div class="cert-chain-label">${this.escapeHtml(item.cert.display_name || item.cert.subject)}</div>
                        <div class="cert-chain-type">${item.type}</div>
                        ${item.cert.is_expired ? '<div class="cert-chain-warning">⚠️ Expired</div>' : ''}
                        ${item.cert.is_expiring_soon && !item.cert.is_expired ? '<div class="cert-chain-warning">⚡ Expiring Soon</div>' : ''}
                    </div>
                    ${index < certs.length - 1 ? '<div class="cert-chain-arrow">↓</div>' : ''}
                `).join('')}
            </div>

            <div class="cert-chain-summary">
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Chain Length:</span>
                    <span class="cert-chain-summary-value">${this.chain.chain_length} certificates</span>
                </div>
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Complete:</span>
                    <span class="cert-chain-summary-value">${this.chain.is_complete ? 'Yes' : 'No'}</span>
                </div>
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Trusted:</span>
                    <span class="cert-chain-summary-value ${this.chain.is_trusted ? 'cert-trusted' : 'cert-untrusted'}">
                        ${this.chain.is_trusted ? 'Yes' : 'No'}
                    </span>
                </div>
            </div>
        `;

        chainViz.innerHTML = chainHtml;

        // Store reference for onclick handlers
        if (!window.certViewers) {
            window.certViewers = {};
        }
        window.certViewers[this.viewerId] = this;
    }

    selectCertificate(index) {
        /**
         * Select a certificate from the chain for detailed view
         */
        if (index === null) {
            this.selectedCert = this.certificate;
        } else if (this.chain) {
            const allCerts = [
                this.chain.leaf,
                ...(this.chain.intermediates || []),
                ...(this.chain.root ? [this.chain.root] : [])
            ];
            this.selectedCert = allCerts[index];
        }

        // Re-render both panels
        this.renderCertificate();
        this.renderChainVisualization();
    }

    async renderD3Tree() {
        /**
         * Render certificate chain using D3.js tree visualization
         * T029: D3.js integration for certificate chain tree
         */
        const chainViz = document.getElementById(`${this.viewerId}-chain-viz`);
        if (!chainViz) return;

        // Load D3.js if not already loaded
        if (!this.d3Loaded && typeof d3 === 'undefined') {
            await this.loadD3();
        }

        if (typeof d3 === 'undefined') {
            console.error('D3.js not loaded, falling back to simple view');
            this.useD3Tree = false;
            this.renderChainVisualization();
            return;
        }

        // Clear existing content
        chainViz.innerHTML = '<div id="' + this.viewerId + '-d3-tree" class="cert-chain-tree"></div>';

        const container = document.getElementById(`${this.viewerId}-d3-tree`);
        const width = container.clientWidth || 350;
        const height = container.clientHeight || 500;

        // Build tree data structure
        const treeData = this.buildTreeData();

        // Create tree layout
        const treeLayout = d3.tree().size([height - 100, width - 150]);

        // Create hierarchy
        const root = d3.hierarchy(treeData);
        treeLayout(root);

        // Create SVG
        const svg = d3.select(`#${this.viewerId}-d3-tree`)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .append('g')
            .attr('transform', 'translate(75, 50)');

        // Add links (edges)
        svg.selectAll('.cert-tree-link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'cert-tree-link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x)
            );

        // Add nodes
        const nodes = svg.selectAll('.cert-tree-node')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'cert-tree-node')
            .attr('transform', d => `translate(${d.y},${d.x})`)
            .on('click', (event, d) => {
                this.selectCertificateFromTree(d.data);
            });

        // Add circles for nodes
        nodes.append('circle')
            .attr('r', 8)
            .style('fill', d => {
                if (d.data.isSelected) return '#0e639c';
                if (d.data.isExpired) return '#da3633';
                if (d.data.isExpiringSoon) return '#bf8700';
                if (d.data.isRoot) return '#1a7f37';
                return '#2d2d30';
            })
            .style('stroke', d => {
                if (d.data.isSelected) return '#1177bb';
                return '#3e3e42';
            });

        // Add labels
        nodes.append('text')
            .attr('dy', '.31em')
            .attr('x', d => d.children ? -12 : 12)
            .style('text-anchor', d => d.children ? 'end' : 'start')
            .text(d => d.data.name);

        // Add summary below tree
        const summaryHtml = `
            <div class="cert-chain-summary" style="margin-top: 20px;">
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Chain Length:</span>
                    <span class="cert-chain-summary-value">${this.chain.chain_length} certificates</span>
                </div>
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Complete:</span>
                    <span class="cert-chain-summary-value">${this.chain.is_complete ? 'Yes' : 'No'}</span>
                </div>
                <div class="cert-chain-summary-item">
                    <span class="cert-chain-summary-label">Trusted:</span>
                    <span class="cert-chain-summary-value ${this.chain.is_trusted ? 'cert-trusted' : 'cert-untrusted'}">
                        ${this.chain.is_trusted ? 'Yes' : 'No'}
                    </span>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', summaryHtml);
    }

    buildTreeData() {
        /**
         * Build hierarchical tree data structure for D3
         */
        if (!this.chain) {
            return {
                name: this.certificate.display_name || this.certificate.subject,
                cert: this.certificate,
                isSelected: true,
                isExpired: this.certificate.is_expired,
                isExpiringSoon: this.certificate.is_expiring_soon
            };
        }

        // Build from root down to leaf (reverse of chain order)
        let currentNode;

        // Start with root
        if (this.chain.root) {
            currentNode = {
                name: this.chain.root.display_name || this.chain.root.subject,
                cert: this.chain.root,
                isSelected: this.selectedCert === this.chain.root,
                isExpired: this.chain.root.is_expired,
                isExpiringSoon: this.chain.root.is_expiring_soon,
                isRoot: true,
                children: []
            };
        }

        // Add intermediates (in reverse order)
        if (this.chain.intermediates && this.chain.intermediates.length > 0) {
            const reversedIntermediates = [...this.chain.intermediates].reverse();

            for (const inter of reversedIntermediates) {
                const interNode = {
                    name: inter.display_name || inter.subject,
                    cert: inter,
                    isSelected: this.selectedCert === inter,
                    isExpired: inter.is_expired,
                    isExpiringSoon: inter.is_expiring_soon,
                    children: []
                };

                if (currentNode) {
                    currentNode.children.push(interNode);
                    currentNode = interNode;
                } else {
                    currentNode = interNode;
                }
            }
        }

        // Add leaf
        const leafNode = {
            name: this.chain.leaf.display_name || this.chain.leaf.subject,
            cert: this.chain.leaf,
            isSelected: this.selectedCert === this.chain.leaf,
            isExpired: this.chain.leaf.is_expired,
            isExpiringSoon: this.chain.leaf.is_expiring_soon
        };

        if (currentNode) {
            currentNode.children.push(leafNode);
            // Return root of tree
            return this.chain.root ? {
                name: this.chain.root.display_name || this.chain.root.subject,
                cert: this.chain.root,
                isSelected: this.selectedCert === this.chain.root,
                isExpired: this.chain.root.is_expired,
                isExpiringSoon: this.chain.root.is_expiring_soon,
                isRoot: true,
                children: currentNode === this.chain.root ? currentNode.children : [currentNode]
            } : currentNode;
        }

        return leafNode;
    }

    selectCertificateFromTree(data) {
        /**
         * Select certificate from D3 tree node click
         */
        this.selectedCert = data.cert;
        this.renderCertificate();
        this.renderD3Tree(); // Re-render tree to update selection
    }

    async loadD3() {
        /**
         * Load D3.js library dynamically
         */
        try {
            const script = document.createElement('script');
            script.src = '/static/vendor/d3/d3.min.js';
            script.async = false;

            await new Promise((resolve, reject) => {
                script.onload = () => {
                    this.d3Loaded = true;
                    resolve();
                };
                script.onerror = reject;
                document.head.appendChild(script);
            });
        } catch (error) {
            console.error('Failed to load D3.js:', error);
            throw error;
        }
    }

    async showExportDialog() {
        /**
         * Show export format selection dialog with proper modal UI
         * T052: Enhanced export dialog with PEM/DER/Text options
         */
        const dialogHtml = `
            <div class="export-dialog-overlay" id="${this.viewerId}-export-overlay">
                <div class="export-dialog">
                    <div class="export-dialog-header">
                        <h3>Export Certificate</h3>
                        <button class="export-dialog-close">✕</button>
                    </div>
                    <div class="export-dialog-body">
                        <div class="export-option">
                            <label>
                                <input type="radio" name="export-format" value="pem" checked>
                                <span class="export-format-label">
                                    <strong>PEM</strong>
                                    <small>Base64-encoded, common format</small>
                                </span>
                            </label>
                        </div>
                        <div class="export-option">
                            <label>
                                <input type="radio" name="export-format" value="der">
                                <span class="export-format-label">
                                    <strong>DER</strong>
                                    <small>Binary format</small>
                                </span>
                            </label>
                        </div>
                        <div class="export-option">
                            <label>
                                <input type="radio" name="export-format" value="text">
                                <span class="export-format-label">
                                    <strong>Text</strong>
                                    <small>Human-readable certificate details</small>
                                </span>
                            </label>
                        </div>
                        <div class="export-info">
                            <p>Certificate: <strong>${this.escapeHtml(this.certificate?.subject || 'Unknown')}</strong></p>
                        </div>
                    </div>
                    <div class="export-dialog-footer">
                        <button class="viewer-btn" onclick="document.getElementById('${this.viewerId}-export-overlay').remove()">Cancel</button>
                        <button class="viewer-btn viewer-btn-primary" id="${this.viewerId}-export-confirm">Export</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);

        // Handle export confirmation
        document.getElementById(`${this.viewerId}-export-confirm`).addEventListener('click', async () => {
            const format = document.querySelector('input[name="export-format"]:checked')?.value || 'pem';
            const overlay = document.getElementById(`${this.viewerId}-export-overlay`);

            await this.exportCertificate(format);
            overlay.remove();
        });

        // Handle close button
        document.querySelector(`#${this.viewerId}-export-overlay .export-dialog-close`).addEventListener('click', () => {
            document.getElementById(`${this.viewerId}-export-overlay`).remove();
        });

        // Handle click outside dialog
        document.getElementById(`${this.viewerId}-export-overlay`).addEventListener('click', (e) => {
            if (e.target.classList.contains('export-dialog-overlay')) {
                e.target.remove();
            }
        });
    }

    async exportCertificate(format) {
        /**
         * Export certificate in specified format
         */
        try {
            const response = await fetch('/api/certificates/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source: this.source,
                    format: format,
                    include_chain: false,
                    port: this.port
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to export certificate');
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `certificate.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

        } catch (error) {
            console.error('Export failed:', error);
            alert(`Export failed: ${error.message}`);
        }
    }

    getSourceName() {
        /**
         * Get display name for the source
         */
        if (this.source.startsWith('http://') || this.source.startsWith('https://')) {
            return this.source.replace(/^https?:\/\//, '');
        }
        return this.source.split('/').pop();
    }

    formatDate(isoString) {
        /**
         * Format ISO date string for display
         */
        const date = new Date(isoString);
        return date.toLocaleString();
    }

    formatTrustStatus(status) {
        /**
         * Format trust status for display
         */
        const statusMap = {
            'trusted': 'Trusted',
            'untrusted': 'Untrusted',
            'expired': 'Expired',
            'not_yet_valid': 'Not Yet Valid',
            'revoked': 'Revoked',
            'unknown': 'Unknown'
        };
        return statusMap[status] || status;
    }

    getFileName() {
        /**
         * Get filename from source
         */
        if (this.source.includes('/')) {
            return this.source.split('/').pop();
        }
        return this.source;
    }

    escapeHtml(text) {
        /**
         * Escape HTML special characters
         */
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in terminal.js
window.CertViewer = CertViewer;
