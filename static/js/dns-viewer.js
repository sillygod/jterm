/**
 * DNS Viewer JavaScript Component
 * Provides DNS record and WHOIS lookup visualization
 *
 * Features:
 * - DNS records display (A, AAAA, MX, NS, TXT, CNAME, SOA, PTR)
 * - WHOIS information display
 * - Tabbed interface for DNS/WHOIS
 * - Export functionality (JSON, text)
 * - Copy to clipboard
 */

class DNSViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `dns-viewer-${Date.now()}`;
        super(viewerId, 'dns');

        // Parse domain from params
        this.domain = params.domain || '';

        // State
        this.dnsData = null;
        this.whoisData = null;
        this.activeTab = 'dns';
        this.isLoading = false;
    }

    async open() {
        /**
         * Open the DNS viewer and load data
         */
        try {
            // Create viewer UI
            await this.createViewer();
            this.show();

            // Load DNS and WHOIS data
            await this.loadData();

        } catch (error) {
            console.error('Failed to open DNS viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the DNS viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container dns-viewer-container" id="${this.viewerId}-container">
                    <!-- Header -->
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">🔍</span>
                            <span>DNS Lookup</span>
                            <span class="viewer-subtitle">${this.escapeHtml(this.domain)}</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn" id="${this.viewerId}-refresh-btn" title="Refresh">
                                ↻ Refresh
                            </button>
                            <button class="viewer-btn" id="${this.viewerId}-export-btn" title="Export data">
                                Export
                            </button>
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>

                    <!-- Tabs -->
                    <div class="dns-tabs">
                        <button class="dns-tab dns-tab-active" data-tab="dns">
                            DNS Records
                        </button>
                        <button class="dns-tab" data-tab="whois">
                            WHOIS
                        </button>
                    </div>

                    <!-- Body -->
                    <div class="viewer-body">
                        <div id="${this.viewerId}-dns-content" class="dns-tab-content dns-tab-content-active">
                            <div class="viewer-loading">
                                <div class="viewer-spinner"></div>
                                <div>Querying DNS records...</div>
                            </div>
                        </div>
                        <div id="${this.viewerId}-whois-content" class="dns-tab-content">
                            <div class="viewer-loading">
                                <div class="viewer-spinner"></div>
                                <div>Querying WHOIS...</div>
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
        // Tab switching
        const tabs = this.container.querySelectorAll('.dns-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Refresh button
        const refreshBtn = document.getElementById(`${this.viewerId}-refresh-btn`);
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        // Export button
        const exportBtn = document.getElementById(`${this.viewerId}-export-btn`);
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.showExportDialog());
        }
    }

    switchTab(tabName) {
        /**
         * Switch between DNS and WHOIS tabs
         */
        this.activeTab = tabName;

        // Update tab buttons
        const tabs = this.container.querySelectorAll('.dns-tab');
        tabs.forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('dns-tab-active');
            } else {
                tab.classList.remove('dns-tab-active');
            }
        });

        // Update tab content
        const dnsContent = document.getElementById(`${this.viewerId}-dns-content`);
        const whoisContent = document.getElementById(`${this.viewerId}-whois-content`);

        if (tabName === 'dns') {
            dnsContent.classList.add('dns-tab-content-active');
            whoisContent.classList.remove('dns-tab-content-active');
        } else {
            dnsContent.classList.remove('dns-tab-content-active');
            whoisContent.classList.add('dns-tab-content-active');
        }
    }

    async loadData() {
        /**
         * Load DNS and WHOIS data from API
         */
        if (this.isLoading) return;
        this.isLoading = true;

        const dnsContent = document.getElementById(`${this.viewerId}-dns-content`);
        const whoisContent = document.getElementById(`${this.viewerId}-whois-content`);

        // Show loading
        dnsContent.innerHTML = `
            <div class="viewer-loading">
                <div class="viewer-spinner"></div>
                <div>Querying DNS records...</div>
            </div>
        `;
        whoisContent.innerHTML = `
            <div class="viewer-loading">
                <div class="viewer-spinner"></div>
                <div>Querying WHOIS...</div>
            </div>
        `;

        try {
            // Call the full lookup API
            const response = await fetch('/api/dns/lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    domain: this.domain
                })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            this.dnsData = data.dns;
            this.whoisData = data.whois;

            // Render results
            this.renderDNSRecords();
            this.renderWHOIS();

        } catch (error) {
            console.error('Failed to load DNS data:', error);
            dnsContent.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-icon">⚠️</div>
                    <div class="viewer-error-message">${this.escapeHtml(error.message)}</div>
                </div>
            `;
            whoisContent.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-icon">⚠️</div>
                    <div class="viewer-error-message">${this.escapeHtml(error.message)}</div>
                </div>
            `;
        } finally {
            this.isLoading = false;
        }
    }

    renderDNSRecords() {
        /**
         * Render DNS records in the viewer
         */
        const content = document.getElementById(`${this.viewerId}-dns-content`);

        if (!this.dnsData || Object.keys(this.dnsData.records).length === 0) {
            content.innerHTML = `
                <div class="dns-info-banner">
                    <div class="dns-info-icon">ℹ️</div>
                    <div class="dns-info-text">
                        <div class="dns-info-title">Domain: ${this.escapeHtml(this.dnsData?.domain || this.domain)}</div>
                        <div class="dns-info-detail">Query time: ${this.dnsData?.query_time || 'N/A'}</div>
                        <div class="dns-info-detail">Nameservers: ${this.dnsData?.nameservers_used?.join(', ') || 'N/A'}</div>
                    </div>
                </div>
                <div class="viewer-empty">
                    <div class="viewer-empty-icon">📭</div>
                    <div class="viewer-empty-message">No DNS records found</div>
                    ${this.dnsData?.error ? `<div class="viewer-empty-hint">${this.escapeHtml(this.dnsData.error)}</div>` : ''}
                </div>
            `;
            return;
        }

        // Record type order and icons
        const recordOrder = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA', 'PTR'];
        const recordIcons = {
            'A': '🌐',
            'AAAA': '🌐',
            'CNAME': '🔗',
            'MX': '📧',
            'NS': '🖥️',
            'TXT': '📝',
            'SOA': '📋',
            'PTR': '↩️'
        };

        let html = `
            <div class="dns-info-banner">
                <div class="dns-info-icon">✅</div>
                <div class="dns-info-text">
                    <div class="dns-info-title">Domain: ${this.escapeHtml(this.dnsData.domain)}</div>
                    <div class="dns-info-detail">Query time: ${this.dnsData.query_time}</div>
                    <div class="dns-info-detail">Nameservers: ${this.dnsData.nameservers_used?.join(', ') || 'N/A'}</div>
                </div>
            </div>
            <div class="dns-records-container">
        `;

        // Sort record types
        const sortedTypes = Object.keys(this.dnsData.records).sort((a, b) => {
            const indexA = recordOrder.indexOf(a);
            const indexB = recordOrder.indexOf(b);
            if (indexA === -1 && indexB === -1) return a.localeCompare(b);
            if (indexA === -1) return 1;
            if (indexB === -1) return -1;
            return indexA - indexB;
        });

        for (const recordType of sortedTypes) {
            const records = this.dnsData.records[recordType];
            const icon = recordIcons[recordType] || '📄';

            html += `
                <div class="dns-record-section">
                    <div class="dns-record-header">
                        <span class="dns-record-icon">${icon}</span>
                        <span class="dns-record-type">${recordType} Records</span>
                        <span class="dns-record-count">${records.length}</span>
                    </div>
                    <div class="dns-record-list">
            `;

            for (const record of records) {
                const ttlFormatted = this.formatTTL(record.ttl);
                const priorityHtml = record.priority !== null
                    ? `<span class="dns-record-priority">Priority: ${record.priority}</span>`
                    : '';

                html += `
                    <div class="dns-record-item">
                        <div class="dns-record-value-row">
                            <span class="dns-record-value">${this.escapeHtml(record.value)}</span>
                            <button class="dns-copy-btn" data-value="${this.escapeHtml(record.value)}" title="Copy to clipboard">
                                📋
                            </button>
                        </div>
                        <div class="dns-record-meta">
                            <span class="dns-record-ttl">TTL: ${ttlFormatted}</span>
                            ${priorityHtml}
                        </div>
                    </div>
                `;
            }

            html += `
                    </div>
                </div>
            `;
        }

        html += '</div>';
        content.innerHTML = html;

        // Setup copy buttons
        content.querySelectorAll('.dns-copy-btn').forEach(btn => {
            btn.addEventListener('click', () => this.copyToClipboard(btn.dataset.value));
        });
    }

    renderWHOIS() {
        /**
         * Render WHOIS information in the viewer
         */
        const content = document.getElementById(`${this.viewerId}-whois-content`);

        if (!this.whoisData || this.whoisData.error) {
            content.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-icon">⚠️</div>
                    <div class="viewer-error-message">${this.escapeHtml(this.whoisData?.error || 'Failed to load WHOIS data')}</div>
                </div>
            `;
            return;
        }

        const fields = [
            { label: 'Domain', value: this.whoisData.domain },
            { label: 'Registrar', value: this.whoisData.registrar },
            { label: 'Registrant', value: this.whoisData.registrant },
            { label: 'Country', value: this.whoisData.registrant_country },
            { label: 'Created', value: this.formatDate(this.whoisData.creation_date) },
            { label: 'Expires', value: this.formatDate(this.whoisData.expiration_date), highlight: this.isExpiringSoon(this.whoisData.expiration_date) },
            { label: 'Updated', value: this.formatDate(this.whoisData.updated_date) },
            { label: 'DNSSEC', value: this.whoisData.dnssec },
        ];

        let html = `
            <div class="whois-container">
                <div class="whois-section">
                    <div class="whois-section-header">Registration Details</div>
                    <div class="whois-fields">
        `;

        for (const field of fields) {
            if (field.value) {
                const highlightClass = field.highlight ? 'whois-field-warning' : '';
                html += `
                    <div class="whois-field ${highlightClass}">
                        <span class="whois-field-label">${field.label}</span>
                        <span class="whois-field-value">${this.escapeHtml(field.value)}</span>
                    </div>
                `;
            }
        }

        html += '</div></div>';

        // Name servers
        if (this.whoisData.name_servers && this.whoisData.name_servers.length > 0) {
            html += `
                <div class="whois-section">
                    <div class="whois-section-header">Name Servers</div>
                    <div class="whois-nameservers">
            `;
            for (const ns of this.whoisData.name_servers) {
                html += `<div class="whois-nameserver">${this.escapeHtml(ns)}</div>`;
            }
            html += '</div></div>';
        }

        // Status
        if (this.whoisData.status && this.whoisData.status.length > 0) {
            html += `
                <div class="whois-section">
                    <div class="whois-section-header">Status</div>
                    <div class="whois-status-list">
            `;
            for (const status of this.whoisData.status) {
                const statusClass = this.getStatusClass(status);
                html += `<div class="whois-status ${statusClass}">${this.escapeHtml(status)}</div>`;
            }
            html += '</div></div>';
        }

        // Emails
        if (this.whoisData.emails && this.whoisData.emails.length > 0) {
            html += `
                <div class="whois-section">
                    <div class="whois-section-header">Contact Emails</div>
                    <div class="whois-emails">
            `;
            for (const email of this.whoisData.emails) {
                html += `<div class="whois-email">${this.escapeHtml(email)}</div>`;
            }
            html += '</div></div>';
        }

        html += '</div>';
        content.innerHTML = html;
    }

    formatTTL(seconds) {
        /**
         * Format TTL in human-readable format
         */
        if (seconds < 60) return `${seconds}s`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
        return `${Math.floor(seconds / 86400)}d`;
    }

    formatDate(dateStr) {
        /**
         * Format ISO date string to readable format
         */
        if (!dateStr) return null;
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateStr;
        }
    }

    isExpiringSoon(dateStr) {
        /**
         * Check if domain is expiring within 30 days
         */
        if (!dateStr) return false;
        try {
            const expiry = new Date(dateStr);
            const now = new Date();
            const daysUntilExpiry = (expiry - now) / (1000 * 60 * 60 * 24);
            return daysUntilExpiry <= 30;
        } catch {
            return false;
        }
    }

    getStatusClass(status) {
        /**
         * Get CSS class for WHOIS status
         */
        const statusLower = status.toLowerCase();
        if (statusLower.includes('clienthold') || statusLower.includes('serverhold')) {
            return 'whois-status-error';
        }
        if (statusLower.includes('pendingdelete') || statusLower.includes('pendingtransfer')) {
            return 'whois-status-warning';
        }
        if (statusLower.includes('ok') || statusLower.includes('active')) {
            return 'whois-status-ok';
        }
        return '';
    }

    async copyToClipboard(text) {
        /**
         * Copy text to clipboard
         */
        try {
            await navigator.clipboard.writeText(text);
            // Show brief feedback
            const btn = this.container.querySelector(`[data-value="${text}"]`);
            if (btn) {
                const originalText = btn.textContent;
                btn.textContent = '✓';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 1000);
            }
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
        }
    }

    showExportDialog() {
        /**
         * Show export format selection dialog
         */
        const dialogHtml = `
            <div class="export-dialog-overlay" id="${this.viewerId}-export-dialog">
                <div class="export-dialog">
                    <div class="export-dialog-header">
                        <h3>Export Data</h3>
                        <button class="export-dialog-close">✕</button>
                    </div>
                    <div class="export-dialog-body">
                        <button class="export-option" data-format="json">
                            <span class="export-icon">📄</span>
                            <span class="export-label">JSON</span>
                            <span class="export-desc">Structured data format</span>
                        </button>
                        <button class="export-option" data-format="text">
                            <span class="export-icon">📝</span>
                            <span class="export-label">Text</span>
                            <span class="export-desc">Plain text format</span>
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', dialogHtml);

        const dialog = document.getElementById(`${this.viewerId}-export-dialog`);
        const closeBtn = dialog.querySelector('.export-dialog-close');

        // Close handlers
        closeBtn.addEventListener('click', () => dialog.remove());
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) dialog.remove();
        });

        // Export handlers
        dialog.querySelectorAll('.export-option').forEach(btn => {
            btn.addEventListener('click', () => {
                this.exportData(btn.dataset.format);
                dialog.remove();
            });
        });
    }

    exportData(format) {
        /**
         * Export data in specified format
         */
        const data = {
            domain: this.domain,
            dns: this.dnsData,
            whois: this.whoisData,
            exported_at: new Date().toISOString()
        };

        let content, filename, mimeType;

        if (format === 'json') {
            content = JSON.stringify(data, null, 2);
            filename = `dns-${this.domain.replace(/\./g, '_')}.json`;
            mimeType = 'application/json';
        } else {
            content = this.formatAsText(data);
            filename = `dns-${this.domain.replace(/\./g, '_')}.txt`;
            mimeType = 'text/plain';
        }

        // Trigger download
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    formatAsText(data) {
        /**
         * Format data as plain text
         */
        let text = `DNS Lookup Report for ${data.domain}\n`;
        text += `Generated: ${data.exported_at}\n`;
        text += '='.repeat(60) + '\n\n';

        // DNS Records
        text += 'DNS RECORDS\n';
        text += '-'.repeat(40) + '\n';

        if (data.dns && data.dns.records) {
            for (const [type, records] of Object.entries(data.dns.records)) {
                text += `\n${type} Records:\n`;
                for (const record of records) {
                    text += `  ${record.value}`;
                    if (record.priority !== null) {
                        text += ` (Priority: ${record.priority})`;
                    }
                    text += ` [TTL: ${record.ttl}]\n`;
                }
            }
        }

        text += '\n';

        // WHOIS
        text += 'WHOIS INFORMATION\n';
        text += '-'.repeat(40) + '\n';

        if (data.whois) {
            const fields = [
                ['Domain', data.whois.domain],
                ['Registrar', data.whois.registrar],
                ['Registrant', data.whois.registrant],
                ['Country', data.whois.registrant_country],
                ['Created', data.whois.creation_date],
                ['Expires', data.whois.expiration_date],
                ['Updated', data.whois.updated_date],
                ['DNSSEC', data.whois.dnssec],
            ];

            for (const [label, value] of fields) {
                if (value) {
                    text += `${label}: ${value}\n`;
                }
            }

            if (data.whois.name_servers && data.whois.name_servers.length > 0) {
                text += '\nName Servers:\n';
                for (const ns of data.whois.name_servers) {
                    text += `  ${ns}\n`;
                }
            }

            if (data.whois.status && data.whois.status.length > 0) {
                text += '\nStatus:\n';
                for (const status of data.whois.status) {
                    text += `  ${status}\n`;
                }
            }
        }

        return text;
    }

    /**
     * Override keyboard shortcuts for DNS viewer
     */
    getKeyboardShortcuts() {
        return [
            {
                title: 'General',
                shortcuts: [
                    { keys: 'Esc', description: 'Close viewer' },
                    { keys: '?', description: 'Show keyboard shortcuts' },
                ]
            },
            {
                title: 'Navigation',
                shortcuts: [
                    { keys: '1', description: 'Switch to DNS Records tab' },
                    { keys: '2', description: 'Switch to WHOIS tab' },
                ]
            },
            {
                title: 'Actions',
                shortcuts: [
                    { keys: 'Ctrl+E', description: 'Export data' },
                    { keys: 'Ctrl+R', description: 'Refresh data' },
                ]
            }
        ];
    }

    handleViewerShortcut(e, isCtrl, isShift) {
        /**
         * Handle viewer-specific keyboard shortcuts
         */
        // Number keys for tab switching
        if (e.key === '1') {
            this.switchTab('dns');
            e.preventDefault();
        } else if (e.key === '2') {
            this.switchTab('whois');
            e.preventDefault();
        }
    }
}

// Export DNSViewer for use
window.DNSViewer = DNSViewer;
