/**
 * Log Viewer JavaScript Component
 * T016: LogViewer class for interactive log viewing
 *
 * Provides:
 * - Log file parsing and display
 * - Real-time filtering and search
 * - Export functionality
 * - Virtual scrolling for large log files
 */

class LogViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `log-viewer-${Date.now()}`;
        super(viewerId, 'log');

        this.filePath = params.filePath || params.file_path;
        this.logFormat = params.logFormat || params.log_format || null;
        this.maxLines = params.maxLines || 1000;

        // State
        this.entries = [];
        this.filteredEntries = [];
        this.statistics = null;
        this.currentFilters = {
            levels: [],
            searchPattern: '',
            since: null,
            until: null,
            source: null
        };

        // Virtual scrolling
        this.virtualScroll = null;
        this.rowHeight = 24; // pixels per row
        this.visibleRows = 50;
    }

    async open() {
        /**
         * Open the log viewer and load initial data
         */
        try {
            // Create viewer UI
            await this.createViewer();
            this.show();

            // Initialize level filters from checked checkboxes
            this.updateLevelFilters();
            console.log('Initial level filters:', this.currentFilters.levels);

            // Show loading state in log list
            const logList = document.getElementById(`${this.viewerId}-log-list`);
            if (logList) {
                logList.innerHTML = `
                    <div class="viewer-loading">
                        <div class="viewer-spinner"></div>
                        <div>Loading log entries...</div>
                    </div>
                `;
            }

            // Load and parse log file
            await this.loadLogFile();
            console.log('Log entries loaded:', this.entries.length, 'entries');
            console.log('Filtered entries:', this.filteredEntries.length, 'entries');

            // Render entries
            this.renderLogEntries();
            console.log('Log entries rendered');

        } catch (error) {
            console.error('Failed to open log viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the log viewer HTML structure
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container" id="${this.viewerId}-container">
                    <!-- Header -->
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">📋</span>
                            <span>Log Viewer</span>
                            <span class="viewer-subtitle">${this.getFileName()}</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn" id="${this.viewerId}-export-btn" title="Export logs">
                                Export
                            </button>
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>

                    <!-- Toolbar with filters -->
                    <div class="viewer-toolbar">
                        <!-- Search -->
                        <div class="viewer-search-box">
                            <input type="text"
                                   class="viewer-search-input"
                                   id="${this.viewerId}-search"
                                   placeholder="Search logs (regex)...">
                        </div>

                        <div class="viewer-toolbar-separator"></div>

                        <!-- Level filters -->
                        <div class="viewer-toolbar-group">
                            <label class="viewer-filter-label">
                                <input type="checkbox" value="ERROR" checked> ERROR
                            </label>
                            <label class="viewer-filter-label">
                                <input type="checkbox" value="WARN" checked> WARN
                            </label>
                            <label class="viewer-filter-label">
                                <input type="checkbox" value="INFO" checked> INFO
                            </label>
                            <label class="viewer-filter-label">
                                <input type="checkbox" value="DEBUG"> DEBUG
                            </label>
                        </div>

                        <div class="viewer-toolbar-separator"></div>

                        <!-- Statistics -->
                        <div id="${this.viewerId}-stats" class="viewer-stats">
                            Loading...
                        </div>
                    </div>

                    <!-- Body with split view -->
                    <div class="viewer-body">
                        <div class="viewer-split">
                            <!-- Left panel: Log entries list -->
                            <div class="viewer-panel viewer-panel-left log-entries-panel">
                                <div class="viewer-panel-header">
                                    Log Entries (<span id="${this.viewerId}-entry-count">0</span>)
                                </div>
                                <div class="viewer-panel-content">
                                    <div id="${this.viewerId}-log-list" class="log-list"></div>
                                </div>
                            </div>

                            <!-- Right panel: Selected entry details -->
                            <div class="viewer-panel log-detail-panel">
                                <div class="viewer-panel-header">Entry Details</div>
                                <div class="viewer-panel-content">
                                    <div id="${this.viewerId}-log-detail" class="log-detail">
                                        <div class="viewer-empty">
                                            <div class="viewer-empty-message">Select a log entry to view details</div>
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
        // Search input
        const searchInput = document.getElementById(`${this.viewerId}-search`);
        if (searchInput) {
            searchInput.addEventListener('input', () => {
                this.currentFilters.searchPattern = searchInput.value;
                this.applyFilters();
            });
        }

        // Level filter checkboxes
        const levelCheckboxes = document.querySelectorAll(`#${this.viewerId}-overlay input[type="checkbox"]`);
        levelCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateLevelFilters();
                this.applyFilters();
            });
        });

        // Export button
        const exportBtn = document.getElementById(`${this.viewerId}-export-btn`);
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.showExportDialog());
        }

        // Close button
        const closeBtn = this.overlay.querySelector('.viewer-btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
    }

    async loadLogFile() {
        /**
         * Load and parse log file from API
         */
        try {
            const response = await this.apiRequest('/api/logs/parse', {
                method: 'POST',
                body: JSON.stringify({
                    file_path: this.filePath,
                    log_format: this.logFormat,
                    max_lines: this.maxLines
                })
            });

            this.entries = response.entries || [];
            this.filteredEntries = [...this.entries];
            this.statistics = response.statistics || {};
            this.logFormat = response.detected_format;

            // Update statistics display
            this.updateStatistics();

        } catch (error) {
            throw new Error(`Failed to load log file: ${error.message}`);
        }
    }

    updateLevelFilters() {
        /**
         * Update level filters from checkboxes
         */
        const checkboxes = document.querySelectorAll(`#${this.viewerId}-overlay input[type="checkbox"]`);
        this.currentFilters.levels = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
    }

    applyFilters() {
        /**
         * Apply current filters to log entries
         */
        this.filteredEntries = this.entries.filter(entry => {
            // Level filter
            if (this.currentFilters.levels.length > 0 &&
                !this.currentFilters.levels.includes(entry.level)) {
                return false;
            }

            // Search pattern filter
            if (this.currentFilters.searchPattern) {
                try {
                    const regex = new RegExp(this.currentFilters.searchPattern, 'i');
                    if (!regex.test(entry.message) && !regex.test(entry.raw_text)) {
                        return false;
                    }
                } catch (e) {
                    // Invalid regex, skip filter
                }
            }

            return true;
        });

        // Re-render with filtered entries
        this.renderLogEntries();
    }

    renderLogEntries() {
        /**
         * Render log entries in the list
         */
        const listContainer = document.getElementById(`${this.viewerId}-log-list`);
        console.log('renderLogEntries - listContainer:', listContainer);
        console.log('renderLogEntries - filteredEntries:', this.filteredEntries);
        if (!listContainer) {
            console.error('Log list container not found!');
            return;
        }

        // Update count
        const countSpan = document.getElementById(`${this.viewerId}-entry-count`);
        if (countSpan) {
            countSpan.textContent = this.filteredEntries.length;
        }

        if (this.filteredEntries.length === 0) {
            listContainer.innerHTML = `
                <div class="viewer-empty">
                    <div class="viewer-empty-message">No log entries match the current filters</div>
                    <div class="viewer-empty-hint">Try adjusting your search or filters</div>
                </div>
            `;
            return;
        }

        // Render entries (simple rendering, virtual scrolling can be added later)
        const html = this.filteredEntries.slice(0, 500).map((entry, index) => {
            const levelClass = `log-level-${entry.level.toLowerCase()}`;
            const isError = entry.is_error ? 'log-entry-error' : '';

            return `
                <div class="log-entry ${levelClass} ${isError}" data-index="${index}">
                    <span class="log-timestamp">${entry.display_time}</span>
                    <span class="log-level viewer-badge viewer-badge-${this.getLevelBadgeClass(entry.level)}">${entry.level}</span>
                    <span class="log-message">${this.escapeHtml(entry.message)}</span>
                </div>
            `;
        }).join('');

        listContainer.innerHTML = html;

        // Add click listeners for entry selection
        listContainer.querySelectorAll('.log-entry').forEach(el => {
            el.addEventListener('click', () => {
                const index = parseInt(el.dataset.index);
                this.showEntryDetails(this.filteredEntries[index]);

                // Highlight selected
                listContainer.querySelectorAll('.log-entry').forEach(e => e.classList.remove('selected'));
                el.classList.add('selected');
            });
        });
    }

    showEntryDetails(entry) {
        /**
         * Show detailed view of selected log entry
         */
        const detailContainer = document.getElementById(`${this.viewerId}-log-detail`);
        if (!detailContainer) return;

        const html = `
            <div class="log-detail-content">
                <h3>Log Entry Details</h3>

                <div class="log-detail-field">
                    <label>Timestamp:</label>
                    <span>${entry.display_time}</span>
                </div>

                <div class="log-detail-field">
                    <label>Level:</label>
                    <span class="viewer-badge viewer-badge-${this.getLevelBadgeClass(entry.level)}">${entry.level}</span>
                </div>

                ${entry.source ? `
                <div class="log-detail-field">
                    <label>Source:</label>
                    <span>${this.escapeHtml(entry.source)}</span>
                </div>
                ` : ''}

                <div class="log-detail-field">
                    <label>Line Number:</label>
                    <span>${entry.line_number}</span>
                </div>

                <div class="log-detail-field">
                    <label>Message:</label>
                    <pre class="log-message-detail">${this.escapeHtml(entry.message)}</pre>
                </div>

                ${entry.stack_trace ? `
                <div class="log-detail-field">
                    <label>Stack Trace:</label>
                    <pre class="log-stack-trace">${this.escapeHtml(entry.stack_trace)}</pre>
                </div>
                ` : ''}

                ${Object.keys(entry.structured_fields || {}).length > 0 ? `
                <div class="log-detail-field">
                    <label>Structured Fields:</label>
                    <pre class="log-structured-fields">${JSON.stringify(entry.structured_fields, null, 2)}</pre>
                </div>
                ` : ''}

                <div class="log-detail-field">
                    <label>Raw Text:</label>
                    <pre class="log-raw-text">${this.escapeHtml(entry.raw_text)}</pre>
                </div>
            </div>
        `;

        detailContainer.innerHTML = html;
    }

    updateStatistics() {
        /**
         * Update statistics display
         */
        const statsContainer = document.getElementById(`${this.viewerId}-stats`);
        if (!statsContainer || !this.statistics) return;

        const totalEntries = this.statistics.total_entries || 0;
        const errorRate = this.statistics.error_rate || 0;

        statsContainer.innerHTML = `
            <span>${totalEntries} entries</span>
            ${errorRate > 0 ? `<span class="stats-error-rate">${errorRate}% errors</span>` : ''}
        `;
    }

    async showExportDialog() {
        /**
         * Show export options dialog
         */
        const format = prompt('Export format (json or csv):', 'json');
        if (!format) return;

        if (!['json', 'csv'].includes(format.toLowerCase())) {
            alert('Invalid format. Please choose json or csv.');
            return;
        }

        try {
            const response = await fetch('/api/logs/export', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_path: this.filePath,
                    format: format.toLowerCase(),
                    levels: this.currentFilters.levels,
                    search_pattern: this.currentFilters.searchPattern || null
                })
            });

            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }

            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `logs.${format.toLowerCase()}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            alert(`Export failed: ${error.message}`);
        }
    }

    getLevelBadgeClass(level) {
        /**
         * Get CSS class for level badge
         */
        const levelMap = {
            'FATAL': 'error',
            'ERROR': 'error',
            'WARN': 'warning',
            'INFO': 'info',
            'DEBUG': 'info',
            'TRACE': 'info'
        };
        return levelMap[level] || 'info';
    }

    getFileName() {
        /**
         * Extract filename from file path
         */
        return this.filePath.split('/').pop();
    }

    escapeHtml(text) {
        /**
         * Escape HTML special characters
         */
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in terminal.js
window.LogViewer = LogViewer;
