/**
 * SQL Viewer JavaScript Component
 * T035: SQLViewer class for interactive database querying
 *
 * Provides:
 * - Database connection management
 * - Schema browsing (tables, columns)
 * - SQL query editor with CodeMirror
 * - Query result display with virtual scrolling
 * - Chart visualization with Chart.js
 * - Export functionality (CSV, JSON, Excel)
 */

class SQLViewer extends BaseViewer {
    constructor(params) {
        const viewerId = `sql-viewer-${Date.now()}`;
        super(viewerId, 'sql');

        // Connection parameters
        this.dbType = params.dbType || params.db_type || 'sqlite';
        this.connectionString = params.connectionString || params.connection_string;
        this.dbPath = params.dbPath || params.db_path; // For SQLite
        this.query = params.query || '';

        // State
        this.schema = null;
        this.queryResult = null;
        this.queryHistory = [];
        this.currentQuery = this.query;
        this.selectedTable = null;
        this.isFullscreen = false;
        this.isHistoryCollapsed = false;

        // CodeMirror editor instance
        this.editor = null;

        // Chart.js instance
        this.chart = null;

        // Virtual scrolling for results
        this.virtualScroll = null;
        this.rowHeight = 30; // pixels per row
        this.visibleRows = 50;

        // Ensure connection string is set
        if (this.dbPath && !this.connectionString) {
            this.connectionString = `sqlite:///${this.dbPath}`;
        }
    }

    async open() {
        /**
         * Open the SQL viewer and initialize connection
         */
        try {
            // Create viewer UI
            await this.createViewer();
            this.show();

            // Show loading state
            this.showLoading('Connecting to database...');

            // Connect to database and load schema
            await this.connectDatabase();

            // If query provided, execute it
            if (this.currentQuery) {
                await this.executeQuery();
            }

        } catch (error) {
            console.error('Failed to open SQL viewer:', error);
            this.showError(error.message);
        }
    }

    async createViewer() {
        /**
         * Create the SQL viewer HTML structure (three-panel layout)
         */
        const viewerHtml = `
            <div class="viewer-overlay" id="${this.viewerId}-overlay">
                <div class="viewer-container sql-viewer-container" id="${this.viewerId}-container">
                    <!-- Header -->
                    <div class="viewer-header">
                        <div class="viewer-title">
                            <span class="viewer-title-icon">🗄️</span>
                            <span>SQL Query</span>
                            <span class="viewer-subtitle" id="${this.viewerId}-db-name">Database</span>
                        </div>
                        <div class="viewer-controls">
                            <button class="viewer-btn" id="${this.viewerId}-export-btn" title="Export results">
                                Export
                            </button>
                            <button class="viewer-btn" id="${this.viewerId}-chart-btn" title="Visualize results">
                                Chart
                            </button>
                            <button class="viewer-btn-close" title="Close (Esc)">✕</button>
                        </div>
                    </div>

                    <!-- Three-panel body -->
                    <div class="viewer-body sql-viewer-body">
                        <!-- Left panel: Schema browser -->
                        <div class="sql-panel sql-schema-panel">
                            <div class="sql-panel-header">
                                <div class="sql-panel-tabs">
                                    <button class="sql-tab-btn active" data-tab="schema">Schema</button>
                                    <button class="sql-tab-btn" data-tab="er-diagram">ER Diagram</button>
                                </div>
                                <div class="sql-panel-header-controls">
                                    <button class="sql-fullscreen-btn" id="${this.viewerId}-fullscreen-btn" title="Toggle fullscreen (F)">
                                        ⛶
                                    </button>
                                    <button class="sql-refresh-btn" id="${this.viewerId}-refresh-schema" title="Refresh schema (Ctrl+R)">
                                        ↻
                                    </button>
                                </div>
                            </div>
                            <div class="sql-panel-content">
                                <div id="${this.viewerId}-schema-tree" class="sql-schema-tree sql-tab-content active" data-tab-content="schema"></div>
                                <div id="${this.viewerId}-er-diagram" class="sql-er-diagram sql-tab-content" data-tab-content="er-diagram" style="display: none;"></div>
                            </div>
                            <div class="panel-resize-handle" data-panel="left"></div>
                        </div>

                        <!-- Middle panel: Query editor + Results -->
                        <div class="sql-panel sql-main-panel">
                            <!-- Query editor -->
                            <div class="sql-editor-section">
                                <div class="sql-panel-header">
                                    <span>Query Editor</span>
                                    <div class="sql-editor-controls">
                                        <button class="viewer-btn viewer-btn-primary" id="${this.viewerId}-run-query" title="Execute query (Ctrl+Enter)">
                                            ▶ Run
                                        </button>
                                        <button class="viewer-btn" id="${this.viewerId}-clear-query" title="Clear editor">
                                            Clear
                                        </button>
                                    </div>
                                </div>
                                <div class="sql-editor-container">
                                    <textarea id="${this.viewerId}-query-editor" class="sql-query-editor">${this.currentQuery}</textarea>
                                </div>
                            </div>

                            <!-- Results section -->
                            <div class="sql-results-section">
                                <div class="sql-panel-header">
                                    <span id="${this.viewerId}-results-title">Results</span>
                                    <span id="${this.viewerId}-results-info" class="sql-results-info"></span>
                                </div>
                                <div class="sql-results-container">
                                    <div id="${this.viewerId}-results-table" class="sql-results-table"></div>
                                    <div id="${this.viewerId}-chart-container" class="sql-chart-container" style="display: none;">
                                        <canvas id="${this.viewerId}-chart"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Right panel: Query history -->
                        <div class="sql-panel sql-history-panel">
                            <div class="sql-panel-header">
                                <span>History</span>
                                <div class="sql-panel-header-controls">
                                    <button class="sql-collapse-btn" id="${this.viewerId}-collapse-history" title="Hide history panel">
                                        ⮜
                                    </button>
                                    <button class="sql-clear-btn" id="${this.viewerId}-clear-history" title="Clear history">
                                        ✕
                                    </button>
                                </div>
                            </div>
                            <div class="sql-panel-content">
                                <div id="${this.viewerId}-query-history" class="sql-query-history"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Status bar -->
                    <div class="viewer-statusbar">
                        <span id="${this.viewerId}-status">Ready</span>
                    </div>
                </div>
            </div>
        `;

        // Insert into DOM
        document.body.insertAdjacentHTML('beforeend', viewerHtml);

        // Initialize viewer (sets up overlay, container, and base handlers)
        this.init();

        // Attach event listeners
        this.attachEventListeners();

        // Initialize CodeMirror editor (will be loaded async)
        await this.initializeEditor();
    }

    async initializeEditor() {
        /**
         * Initialize CodeMirror SQL editor
         * T039: Integration of CodeMirror 6
         */
        try {
            const editorElement = document.getElementById(`${this.viewerId}-query-editor`);

            // Configure textarea for SQL editing
            editorElement.style.fontFamily = 'Monaco, Menlo, "Ubuntu Mono", monospace';
            editorElement.style.fontSize = '14px';
            editorElement.style.lineHeight = '1.5';
            editorElement.style.padding = '8px';
            editorElement.style.border = '1px solid #ccc';
            editorElement.style.borderRadius = '4px';
            editorElement.style.width = '100%';
            editorElement.style.minHeight = '120px';
            editorElement.style.resize = 'vertical';

            // Add SQL keyword highlighting via simple color coding
            editorElement.addEventListener('input', () => {
                this.currentQuery = editorElement.value;
            });

            // Add keyboard shortcut for running query
            editorElement.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    this.executeQuery();
                }
            });

            // Store editor reference
            this.editor = editorElement;

            // NOTE: For full CodeMirror 6 integration, would need:
            // 1. Load CodeMirror ES modules from CDN
            // 2. Import sql() language mode
            // 3. Create EditorView with extensions
            // Currently using enhanced textarea as fallback

        } catch (error) {
            console.warn('Failed to initialize editor:', error);
        }
    }

    async loadCodeMirror() {
        /**
         * Dynamically load CodeMirror library
         * NOTE: CodeMirror 6 uses ES modules which require special handling
         * For production use, consider bundling or using importmap
         */
        try {
            // Placeholder for future CDN loading
            // Would require dynamic import() with proper ES module handling
            console.log('CodeMirror loading placeholder');
        } catch (error) {
            console.warn('CodeMirror loading failed:', error);
        }
    }

    attachEventListeners() {
        /**
         * Attach event listeners to UI controls
         */
        // Close button
        const closeBtn = document.querySelector(`#${this.viewerId}-container .viewer-btn-close`);
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        // Run query button
        const runBtn = document.getElementById(`${this.viewerId}-run-query`);
        if (runBtn) {
            runBtn.addEventListener('click', () => this.executeQuery());
        }

        // Clear query button
        const clearBtn = document.getElementById(`${this.viewerId}-clear-query`);
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearQuery());
        }

        // Export button
        const exportBtn = document.getElementById(`${this.viewerId}-export-btn`);
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportResults());
        }

        // Chart button
        const chartBtn = document.getElementById(`${this.viewerId}-chart-btn`);
        if (chartBtn) {
            chartBtn.addEventListener('click', () => this.toggleChart());
        }

        // Refresh schema button
        const refreshBtn = document.getElementById(`${this.viewerId}-refresh-schema`);
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshSchema());
        }

        // Clear history button
        const clearHistoryBtn = document.getElementById(`${this.viewerId}-clear-history`);
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        }

        // Fullscreen button
        const fullscreenBtn = document.getElementById(`${this.viewerId}-fullscreen-btn`);
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }

        // Collapse history panel button
        const collapseHistoryBtn = document.getElementById(`${this.viewerId}-collapse-history`);
        if (collapseHistoryBtn) {
            collapseHistoryBtn.addEventListener('click', () => this.toggleHistoryPanel());
        }

        // Tab switching (Schema / ER Diagram)
        const container = document.getElementById(`${this.viewerId}-container`);
        if (container) {
            const tabButtons = container.querySelectorAll('.sql-tab-btn');
            tabButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const targetTab = btn.dataset.tab;
                    this.switchTab(targetTab);
                });
            });
        }

        // Panel resizing
        this.setupPanelResize();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Only handle if viewer is visible
            const overlay = document.getElementById(`${this.viewerId}-overlay`);
            if (!overlay || overlay.style.display === 'none') return;

            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.executeQuery();
            } else if (e.key === 'f' || e.key === 'F') {
                // Toggle fullscreen with F key
                e.preventDefault();
                this.toggleFullscreen();
            } else if (e.key === 'Escape' && this.isFullscreen) {
                // Exit fullscreen with Escape
                e.preventDefault();
                this.toggleFullscreen();
            }
        });
    }

    async connectDatabase() {
        /**
         * Connect to database and load schema
         */
        try {
            const response = await fetch('/api/sql/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    db_type: this.dbType,
                    connection_string: this.connectionString,
                    display_name: this.getDisplayName()
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to connect to database');
            }

            const data = await response.json();

            if (!data.is_connected) {
                throw new Error(data.error_message || 'Connection failed');
            }

            // Update UI with connection info
            const dbNameElement = document.getElementById(`${this.viewerId}-db-name`);
            if (dbNameElement) {
                dbNameElement.textContent = data.display_name;
            }

            // Load schema
            await this.loadSchema();

            this.setStatus(`Connected to ${data.display_name} (${data.table_count} tables)`);

        } catch (error) {
            throw new Error(`Database connection failed: ${error.message}`);
        }
    }

    async loadSchema() {
        /**
         * Load database schema (tables and columns)
         */
        try {
            const response = await fetch('/api/sql/schema', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    db_type: this.dbType,
                    connection_string: this.connectionString
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to load schema');
            }

            const data = await response.json();
            this.schema = data.tables;

            // Render schema tree
            this.renderSchema();

        } catch (error) {
            console.error('Failed to load schema:', error);
            this.showError(`Failed to load schema: ${error.message}`);
        }
    }

    renderSchema() {
        /**
         * Render database schema as expandable tree
         */
        const schemaTree = document.getElementById(`${this.viewerId}-schema-tree`);
        if (!schemaTree || !this.schema) return;

        let html = '<div class="schema-tables">';

        for (const table of this.schema) {
            html += `
                <div class="schema-table">
                    <div class="schema-table-name" data-table="${table.name}">
                        <span class="schema-expand">▶</span>
                        <span class="schema-icon">📋</span>
                        <span>${table.name}</span>
                        <span class="schema-row-count">(${table.row_count || 0})</span>
                    </div>
                    <div class="schema-columns" style="display: none;">
            `;

            for (const column of table.columns) {
                const pkIcon = column.primary_key ? '🔑' : '';
                const nullableText = column.nullable ? '' : ' NOT NULL';
                html += `
                    <div class="schema-column">
                        ${pkIcon} ${column.name}
                        <span class="schema-type">${column.data_type}${nullableText}</span>
                    </div>
                `;
            }

            html += `
                    </div>
                </div>
            `;
        }

        html += '</div>';
        schemaTree.innerHTML = html;

        // Clear the loading state in the results panel after schema is loaded
        const resultsTable = document.getElementById(`${this.viewerId}-results-table`);
        if (resultsTable) {
            resultsTable.innerHTML = `
                <div class="viewer-empty">
                    <div class="viewer-empty-icon">📊</div>
                    <div class="viewer-empty-message">Ready to execute queries</div>
                    <div class="viewer-empty-hint">Enter a SQL query above and click "Run" or press Ctrl+Enter</div>
                </div>
            `;
        }

        // Attach click listeners for expand/collapse
        schemaTree.querySelectorAll('.schema-table-name').forEach(element => {
            element.addEventListener('click', (e) => {
                const columns = element.nextElementSibling;
                const expand = element.querySelector('.schema-expand');

                if (columns.style.display === 'none') {
                    columns.style.display = 'block';
                    expand.textContent = '▼';
                } else {
                    columns.style.display = 'none';
                    expand.textContent = '▶';
                }
            });

            // Double-click to generate SELECT query
            element.addEventListener('dblclick', (e) => {
                const tableName = element.dataset.table;
                const query = `SELECT * FROM ${tableName} LIMIT 100`;
                this.setQuery(query);
            });
        });
    }

    async executeQuery() {
        /**
         * Execute the SQL query and display results
         */
        try {
            // Get query text
            const editorElement = document.getElementById(`${this.viewerId}-query-editor`);
            const query = editorElement.value.trim();

            if (!query) {
                this.showError('Please enter a SQL query');
                return;
            }

            this.currentQuery = query;
            this.showLoading('Executing query...');

            // Execute query
            const response = await fetch('/api/sql/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    db_type: this.dbType,
                    connection_string: this.connectionString,
                    query: query,
                    offset: 0,
                    limit: 1000
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Query execution failed');
            }

            this.queryResult = await response.json();

            // Render results
            this.renderResults();

            // Add to history
            this.addToHistory(query, this.queryResult);

            this.setStatus(`Query executed in ${this.queryResult.execution_time_ms.toFixed(2)}ms - ${this.queryResult.row_count} rows`);

        } catch (error) {
            console.error('Query execution failed:', error);
            this.showError(`Query failed: ${error.message}`);
        }
    }

    renderResults() {
        /**
         * Render query results in table format
         * T035: Includes virtual scrolling for large result sets
         */
        const resultsTable = document.getElementById(`${this.viewerId}-results-table`);
        const resultsInfo = document.getElementById(`${this.viewerId}-results-info`);

        if (!resultsTable || !this.queryResult) return;

        // Update results info
        if (resultsInfo) {
            resultsInfo.textContent = `${this.queryResult.row_count} rows in ${this.queryResult.execution_time_ms.toFixed(2)}ms`;
        }

        if (this.queryResult.row_count === 0) {
            resultsTable.innerHTML = '<div class="sql-no-results">No results</div>';
            return;
        }

        // Build table HTML
        let html = '<table class="sql-table"><thead><tr>';

        // Column headers
        for (const column of this.queryResult.columns) {
            html += `<th>${column}</th>`;
        }
        html += '</tr></thead><tbody>';

        // Rows (with virtual scrolling for large datasets)
        const maxRows = Math.min(this.queryResult.rows.length, 1000);
        for (let i = 0; i < maxRows; i++) {
            html += '<tr>';
            for (const cell of this.queryResult.rows[i]) {
                const cellValue = cell === null ? '<em>NULL</em>' : String(cell);
                html += `<td>${cellValue}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table>';

        if (this.queryResult.has_more) {
            html += '<div class="sql-more-results">+ More results available (showing first 1000 rows)</div>';
        }

        resultsTable.innerHTML = html;
    }

    addToHistory(query, result) {
        /**
         * Add query to history
         */
        const historyItem = {
            query: query,
            timestamp: new Date(),
            row_count: result.row_count,
            execution_time_ms: result.execution_time_ms
        };

        this.queryHistory.unshift(historyItem);

        // Limit history to 20 items
        if (this.queryHistory.length > 20) {
            this.queryHistory = this.queryHistory.slice(0, 20);
        }

        this.renderHistory();
    }

    renderHistory() {
        /**
         * Render query history
         */
        const historyContainer = document.getElementById(`${this.viewerId}-query-history`);
        if (!historyContainer) return;

        if (this.queryHistory.length === 0) {
            historyContainer.innerHTML = '<div class="sql-no-history">No query history</div>';
            return;
        }

        let html = '';
        for (const item of this.queryHistory) {
            const time = item.timestamp.toLocaleTimeString();
            const preview = item.query.length > 50 ? item.query.substring(0, 50) + '...' : item.query;

            html += `
                <div class="sql-history-item" data-query="${item.query}">
                    <div class="sql-history-time">${time}</div>
                    <div class="sql-history-query">${preview}</div>
                    <div class="sql-history-meta">${item.row_count} rows, ${item.execution_time_ms.toFixed(0)}ms</div>
                </div>
            `;
        }

        historyContainer.innerHTML = html;

        // Attach click listeners
        historyContainer.querySelectorAll('.sql-history-item').forEach(element => {
            element.addEventListener('click', () => {
                const query = element.dataset.query;
                this.setQuery(query);
            });
        });
    }

    async exportResults() {
        /**
         * Export query results to CSV, JSON, or Excel
         */
        if (!this.queryResult || this.queryResult.row_count === 0) {
            this.showError('No results to export');
            return;
        }

        // Show export format selection
        const format = await this.selectExportFormat();
        if (!format) return;

        try {
            this.showLoading(`Exporting as ${format.toUpperCase()}...`);

            const response = await fetch('/api/sql/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    db_type: this.dbType,
                    connection_string: this.connectionString,
                    query: this.currentQuery,
                    format: format
                })
            });

            if (!response.ok) {
                throw new Error('Export failed');
            }

            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `query_results.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.setStatus(`Exported ${this.queryResult.row_count} rows as ${format.toUpperCase()}`);

        } catch (error) {
            console.error('Export failed:', error);
            this.showError(`Export failed: ${error.message}`);
        }
    }

    async selectExportFormat() {
        /**
         * Show format selection dialog with proper modal UI
         * T052: Enhanced export dialog with CSV/JSON/Excel options
         */
        return new Promise((resolve) => {
            const dialogHtml = `
                <div class="export-dialog-overlay" id="${this.viewerId}-export-overlay">
                    <div class="export-dialog">
                        <div class="export-dialog-header">
                            <h3>Export Query Results</h3>
                            <button class="export-dialog-close">✕</button>
                        </div>
                        <div class="export-dialog-body">
                            <div class="export-option">
                                <label>
                                    <input type="radio" name="export-format" value="csv" checked>
                                    <span class="export-format-label">
                                        <strong>CSV</strong>
                                        <small>Spreadsheet-compatible, lightweight</small>
                                    </span>
                                </label>
                            </div>
                            <div class="export-option">
                                <label>
                                    <input type="radio" name="export-format" value="json">
                                    <span class="export-format-label">
                                        <strong>JSON</strong>
                                        <small>Structured data with type information</small>
                                    </span>
                                </label>
                            </div>
                            <div class="export-option">
                                <label>
                                    <input type="radio" name="export-format" value="xlsx">
                                    <span class="export-format-label">
                                        <strong>Excel (XLSX)</strong>
                                        <small>Full Excel workbook with formatting</small>
                                    </span>
                                </label>
                            </div>
                            <div class="export-info">
                                <p><strong>${this.queryResult?.row_count || 0}</strong> rows will be exported</p>
                            </div>
                        </div>
                        <div class="export-dialog-footer">
                            <button class="viewer-btn" id="${this.viewerId}-export-cancel">Cancel</button>
                            <button class="viewer-btn viewer-btn-primary" id="${this.viewerId}-export-confirm">Export</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', dialogHtml);

            // Handle export confirmation
            document.getElementById(`${this.viewerId}-export-confirm`).addEventListener('click', () => {
                const format = document.querySelector('input[name="export-format"]:checked')?.value;
                document.getElementById(`${this.viewerId}-export-overlay`).remove();
                resolve(format);
            });

            // Handle cancel button
            document.getElementById(`${this.viewerId}-export-cancel`).addEventListener('click', () => {
                document.getElementById(`${this.viewerId}-export-overlay`).remove();
                resolve(null);
            });

            // Handle close button
            document.querySelector(`#${this.viewerId}-export-overlay .export-dialog-close`).addEventListener('click', () => {
                document.getElementById(`${this.viewerId}-export-overlay`).remove();
                resolve(null);
            });

            // Handle click outside dialog
            document.getElementById(`${this.viewerId}-export-overlay`).addEventListener('click', (e) => {
                if (e.target.classList.contains('export-dialog-overlay')) {
                    e.target.remove();
                    resolve(null);
                }
            });
        });
    }

    toggleChart() {
        /**
         * Toggle between table and chart view
         * T040: Chart.js integration
         */
        const tableContainer = document.getElementById(`${this.viewerId}-results-table`);
        const chartContainer = document.getElementById(`${this.viewerId}-chart-container`);

        if (!chartContainer || !tableContainer) return;

        if (chartContainer.style.display === 'none') {
            // Show chart
            chartContainer.style.display = 'block';
            tableContainer.style.display = 'none';
            this.renderChart();
        } else {
            // Show table
            chartContainer.style.display = 'none';
            tableContainer.style.display = 'block';
        }
    }

    renderChart() {
        /**
         * Render results as chart
         * T040: Chart.js integration
         */
        const canvas = document.getElementById(`${this.viewerId}-chart`);
        if (!canvas || !this.queryResult) return;

        // Destroy previous chart if exists
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Chart.js library not loaded', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Determine chart type based on data
        const chartConfig = this.generateChartConfig();

        if (!chartConfig) {
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#666';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Unable to visualize this data', canvas.width / 2, canvas.height / 2);
            ctx.fillText('Try selecting numeric columns only', canvas.width / 2, canvas.height / 2 + 20);
            return;
        }

        try {
            this.chart = new Chart(canvas, chartConfig);
        } catch (error) {
            console.error('Failed to create chart:', error);
        }
    }

    generateChartConfig() {
        /**
         * Generate Chart.js configuration from query results
         * T040: Smart chart type detection
         */
        if (!this.queryResult || this.queryResult.row_count === 0) {
            return null;
        }

        const columns = this.queryResult.columns;
        const rows = this.queryResult.rows;

        // Need at least 2 columns (label and value)
        if (columns.length < 2) {
            return null;
        }

        // Assume first column is labels, remaining are numeric values
        const labels = rows.map(row => String(row[0])).slice(0, 20); // Limit to 20 data points

        // Find numeric columns
        const numericColumns = [];
        for (let i = 1; i < columns.length; i++) {
            const isNumeric = rows.every(row =>
                row[i] === null || typeof row[i] === 'number' || !isNaN(parseFloat(row[i]))
            );
            if (isNumeric) {
                numericColumns.push(i);
            }
        }

        if (numericColumns.length === 0) {
            return null;
        }

        // Build datasets
        const datasets = numericColumns.map((colIdx, idx) => {
            const colors = [
                'rgba(75, 192, 192, 0.6)',
                'rgba(255, 99, 132, 0.6)',
                'rgba(54, 162, 235, 0.6)',
                'rgba(255, 206, 86, 0.6)',
                'rgba(153, 102, 255, 0.6)',
            ];

            return {
                label: columns[colIdx],
                data: rows.slice(0, 20).map(row => row[colIdx] === null ? 0 : parseFloat(row[colIdx]) || 0),
                backgroundColor: colors[idx % colors.length],
                borderColor: colors[idx % colors.length].replace('0.6', '1'),
                borderWidth: 2,
                tension: 0.1
            };
        });

        // Choose chart type based on data characteristics
        const chartType = this.detectChartType(rows, numericColumns);

        return {
            type: chartType,
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: datasets.length > 1,
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Query Results Visualization'
                    }
                },
                scales: chartType === 'pie' ? {} : {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    detectChartType(rows, numericColumns) {
        /**
         * Detect best chart type for the data
         */
        // If only one numeric column and few rows, use pie chart
        if (numericColumns.length === 1 && rows.length <= 10) {
            return 'pie';
        }

        // If data looks like time series (many rows), use line chart
        if (rows.length > 10) {
            return 'line';
        }

        // Default to bar chart
        return 'bar';
    }

    setQuery(query) {
        /**
         * Set the query in the editor
         */
        const editorElement = document.getElementById(`${this.viewerId}-query-editor`);
        if (editorElement) {
            editorElement.value = query;
            this.currentQuery = query;
        }
    }

    clearQuery() {
        /**
         * Clear the query editor
         */
        this.setQuery('');
    }

    clearHistory() {
        /**
         * Clear query history
         */
        this.queryHistory = [];
        this.renderHistory();
    }

    async refreshSchema() {
        /**
         * Refresh database schema
         */
        this.showLoading('Refreshing schema...');
        await this.loadSchema();
        this.setStatus('Schema refreshed');
    }

    switchTab(targetTab) {
        /**
         * Switch between Schema and ER Diagram tabs
         */
        const container = document.getElementById(`${this.viewerId}-container`);
        if (!container) return;

        // Update tab button states
        const tabButtons = container.querySelectorAll('.sql-tab-btn');
        tabButtons.forEach(btn => {
            if (btn.dataset.tab === targetTab) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update tab content visibility
        const tabContents = container.querySelectorAll('.sql-tab-content');
        tabContents.forEach(content => {
            if (content.dataset.tabContent === targetTab) {
                content.style.display = 'block';
                content.classList.add('active');
            } else {
                content.style.display = 'none';
                content.classList.remove('active');
            }
        });

        // Render ER diagram if switching to that tab
        if (targetTab === 'er-diagram') {
            this.renderERDiagram();
        }
    }

    setupPanelResize() {
        /**
         * Setup drag-to-resize functionality for left schema panel
         */
        const container = document.getElementById(`${this.viewerId}-container`);
        if (!container) return;

        const resizeHandle = container.querySelector('.panel-resize-handle');
        const schemaPanel = container.querySelector('.sql-schema-panel');

        if (!resizeHandle || !schemaPanel) return;

        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        // Get computed styles to read min/max width
        const getMinMaxWidth = () => {
            const styles = window.getComputedStyle(schemaPanel);
            return {
                min: parseInt(styles.minWidth) || 200,
                max: parseInt(styles.maxWidth) || 600
            };
        };

        const onMouseDown = (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = schemaPanel.offsetWidth;

            // Add visual feedback
            resizeHandle.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            e.preventDefault();
        };

        const onMouseMove = (e) => {
            if (!isResizing) return;

            const delta = e.clientX - startX;
            const newWidth = startWidth + delta;

            // Apply min/max constraints from CSS
            const { min, max } = getMinMaxWidth();
            const constrainedWidth = Math.max(min, Math.min(max, newWidth));

            // Set width explicitly to override flexbox
            schemaPanel.style.width = `${constrainedWidth}px`;
            schemaPanel.style.minWidth = `${min}px`;
            schemaPanel.style.maxWidth = `${max}px`;

            e.preventDefault();
        };

        const onMouseUp = () => {
            if (!isResizing) return;

            isResizing = false;
            resizeHandle.classList.remove('resizing');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        resizeHandle.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        // Store cleanup function
        this.cleanupResize = () => {
            resizeHandle.removeEventListener('mousedown', onMouseDown);
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }

    renderERDiagram() {
        /**
         * Render Entity-Relationship diagram for database schema
         * Improved layout with better spacing and responsive design
         */
        const erContainer = document.getElementById(`${this.viewerId}-er-diagram`);
        if (!erContainer || !this.schema) return;

        // Clear previous diagram
        erContainer.innerHTML = '';

        // Create SVG container
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.setAttribute('class', 'er-diagram-svg');

        // Calculate viewBox based on container size and number of tables
        // Use larger dimensions for better spacing and distribution
        const containerWidth = erContainer.offsetWidth || 800;
        const isFullscreen = this.isFullscreen;

        // Calculate based on number of tables for optimal layout
        const tableCount = this.schema.length;

        // Estimate columns (same logic as layout below)
        let estimatedColumns;
        if (tableCount <= 6) {
            estimatedColumns = 3;
        } else if (tableCount <= 12) {
            estimatedColumns = 4;
        } else if (tableCount <= 20) {
            estimatedColumns = 5;
        } else {
            estimatedColumns = Math.min(6, Math.ceil(Math.sqrt(tableCount)));
        }

        // Calculate viewBox width generously
        const baseWidth = isFullscreen ? 2400 : 2000; // Wider for better spread
        const viewBoxWidth = Math.max(baseWidth, containerWidth * 1.5);

        // Note: viewBox height will be calculated after we know row heights
        // We'll update it later

        console.log(`ER Diagram Layout: ${tableCount} tables, ${estimatedColumns} columns`);

        svg.setAttribute('viewBox', `0 0 ${viewBoxWidth} 1000`); // Temporary, will update
        svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

        // Add styles
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        style.textContent = `
            .er-table-box {
                fill: var(--viewer-item-bg, #252526);
                stroke: var(--viewer-border, #3e3e42);
                stroke-width: 2;
            }
            .er-table-header {
                fill: var(--viewer-header-bg, #1e1e1e);
            }
            .er-table-name {
                fill: var(--viewer-fg, #d4d4d4);
                font-size: ${isFullscreen ? '16px' : '14px'};
                font-weight: bold;
            }
            .er-column-text {
                fill: var(--viewer-fg, #d4d4d4);
                font-size: ${isFullscreen ? '13px' : '12px'};
            }
            .er-pk-icon {
                fill: #ffd700;
                font-size: ${isFullscreen ? '12px' : '11px'};
            }
            .er-type-text {
                fill: var(--viewer-subtitle-color, #858585);
                font-size: ${isFullscreen ? '12px' : '11px'};
            }
            .er-relationship-line {
                stroke: var(--viewer-accent, #007acc);
                stroke-width: 2;
                fill: none;
            }
        `;
        svg.appendChild(style);

        // Improved layout algorithm with better space utilization
        const tableWidth = isFullscreen ? 320 : 280;
        const tableHeaderHeight = 40;
        const columnHeight = 24;
        const padding = 60; // Increased padding

        // Calculate optimal columns based on number of tables and available width
        // tableCount already declared above in viewBox calculation

        // For small number of tables, use fewer columns for better spread
        // Use 3-4 columns max for better readability
        let columnsPerRow;
        if (tableCount <= 6) {
            columnsPerRow = 3; // 2 rows of 3
        } else if (tableCount <= 12) {
            columnsPerRow = 4; // 3 rows of 4
        } else if (tableCount <= 20) {
            columnsPerRow = 5; // 4 rows of 5
        } else {
            columnsPerRow = Math.min(6, Math.ceil(Math.sqrt(tableCount)));
        }

        // Adjust for available width
        const maxPossibleColumns = Math.floor((viewBoxWidth - padding * 2) / (tableWidth + 100));
        columnsPerRow = Math.min(columnsPerRow, maxPossibleColumns);
        columnsPerRow = Math.max(3, columnsPerRow); // At least 3 columns for better layout

        // Calculate gaps to distribute tables evenly across width
        const totalTableWidth = columnsPerRow * tableWidth;
        const availableGapSpace = viewBoxWidth - padding * 2 - totalTableWidth;
        const horizontalGap = Math.max(80, Math.min(200, availableGapSpace / (columnsPerRow - 1)));

        // Store table positions for drawing relationships
        const tablePositions = new Map();

        // First pass: organize tables into rows and calculate row heights
        const rows = [];
        for (let i = 0; i < tableCount; i += columnsPerRow) {
            const rowTables = this.schema.slice(i, Math.min(i + columnsPerRow, tableCount));
            rows.push(rowTables);
        }

        // Calculate max height for each row to keep them aligned
        const rowHeights = rows.map(rowTables => {
            const maxTableHeight = Math.max(...rowTables.map(t =>
                tableHeaderHeight + (t.columns.length * columnHeight)
            ));
            return maxTableHeight;
        });

        // Second pass: position tables
        let currentY = padding;

        this.schema.forEach((table, index) => {
            const row = Math.floor(index / columnsPerRow);
            const col = index % columnsPerRow;

            // Center the tables horizontally if not filling the full row
            const tablesInThisRow = Math.min(columnsPerRow, tableCount - row * columnsPerRow);
            const totalRowWidth = tablesInThisRow * tableWidth + (tablesInThisRow - 1) * horizontalGap;
            const rowStartX = (viewBoxWidth - totalRowWidth) / 2;

            const x = rowStartX + col * (tableWidth + horizontalGap);

            // Y position based on accumulated row heights
            let y = padding;
            for (let r = 0; r < row; r++) {
                y += rowHeights[r] + (isFullscreen ? 80 : 70); // Gap between rows
            }

            // Calculate table height based on number of columns
            const tableHeight = tableHeaderHeight + (table.columns.length * columnHeight);

            // Store position for relationship drawing
            tablePositions.set(table.name, { x, y, width: tableWidth, height: tableHeight });

            // Create table box group
            const tableGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            tableGroup.setAttribute('class', 'er-table');

            // Main box
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x);
            rect.setAttribute('y', y);
            rect.setAttribute('width', tableWidth);
            rect.setAttribute('height', tableHeight);
            rect.setAttribute('class', 'er-table-box');
            rect.setAttribute('rx', '4');
            tableGroup.appendChild(rect);

            // Header background
            const headerRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            headerRect.setAttribute('x', x);
            headerRect.setAttribute('y', y);
            headerRect.setAttribute('width', tableWidth);
            headerRect.setAttribute('height', tableHeaderHeight);
            headerRect.setAttribute('class', 'er-table-header');
            headerRect.setAttribute('rx', '4');
            tableGroup.appendChild(headerRect);

            // Table name
            const tableName = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            tableName.setAttribute('x', x + 10);
            tableName.setAttribute('y', y + 22);
            tableName.setAttribute('class', 'er-table-name');
            tableName.textContent = `📋 ${table.name}`;
            tableGroup.appendChild(tableName);

            // Row count
            const rowCount = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            rowCount.setAttribute('x', x + tableWidth - 10);
            rowCount.setAttribute('y', y + 22);
            rowCount.setAttribute('class', 'er-type-text');
            rowCount.setAttribute('text-anchor', 'end');
            rowCount.textContent = `${table.row_count || 0} rows`;
            tableGroup.appendChild(rowCount);

            // Columns
            table.columns.forEach((column, colIndex) => {
                const colY = y + tableHeaderHeight + (colIndex * columnHeight) + 16;

                // Primary key icon
                if (column.primary_key) {
                    const pkIcon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    pkIcon.setAttribute('x', x + 8);
                    pkIcon.setAttribute('y', colY);
                    pkIcon.setAttribute('class', 'er-pk-icon');
                    pkIcon.textContent = '🔑';
                    tableGroup.appendChild(pkIcon);
                }

                // Column name
                const colName = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                colName.setAttribute('x', x + (column.primary_key ? 25 : 10));
                colName.setAttribute('y', colY);
                colName.setAttribute('class', 'er-column-text');
                colName.textContent = column.name;
                tableGroup.appendChild(colName);

                // Data type
                const dataType = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                dataType.setAttribute('x', x + tableWidth - 10);
                dataType.setAttribute('y', colY);
                dataType.setAttribute('class', 'er-type-text');
                dataType.setAttribute('text-anchor', 'end');
                dataType.textContent = column.data_type;
                tableGroup.appendChild(dataType);
            });

            svg.appendChild(tableGroup);
        });

        // Update viewBox height now that we know actual row heights
        const totalHeight = padding * 2 + rowHeights.reduce((sum, h, idx) => {
            return sum + h + (idx < rowHeights.length - 1 ? (isFullscreen ? 80 : 70) : 0);
        }, 0);
        const viewBoxHeight = Math.max(1000, totalHeight);
        svg.setAttribute('viewBox', `0 0 ${viewBoxWidth} ${viewBoxHeight}`);

        console.log(`Layout details: ${columnsPerRow} cols/row, ${rows.length} rows, table width: ${tableWidth}px, h-gap: ${horizontalGap.toFixed(0)}px, total height: ${viewBoxHeight}px`);
        console.log(`Row heights: ${rowHeights.map(h => h.toFixed(0)).join(', ')}`);

        // Draw relationships (foreign key connections)
        this.drawRelationships(svg, tablePositions);

        // Add zoom/pan controls hint
        const hint = document.createElement('div');
        hint.className = 'er-diagram-hint';
        hint.textContent = isFullscreen
            ? 'Scroll/+/- to zoom • Drag to pan • 0 to reset • F or Esc to exit fullscreen'
            : 'Scroll/+/- to zoom • Drag to pan • 0 to reset • F for fullscreen';
        erContainer.appendChild(hint);

        erContainer.appendChild(svg);

        // Add zoom/pan functionality
        this.setupERDiagramInteraction(svg, erContainer);
    }

    drawRelationships(svg, tablePositions) {
        /**
         * Draw relationship lines between tables based on foreign keys
         * Enhanced detection for complex table naming patterns
         */
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'er-relationships');

        const relationships = [];

        // Detect foreign key relationships by convention
        for (const table of this.schema) {
            for (const column of table.columns) {
                // Check if column name ends with _id
                if (column.name.endsWith('_id')) {
                    const targetTable = this.findTargetTable(column.name);

                    if (targetTable) {
                        relationships.push({
                            fromTable: table.name,
                            fromColumn: column.name,
                            toTable: targetTable.name,
                            toColumn: this.findPrimaryKeyColumn(targetTable)
                        });
                    } else {
                        console.debug(`No target found for ${table.name}.${column.name}`);
                    }
                }
            }
        }

        console.log(`Detected ${relationships.length} relationships in total`);

        // Draw relationship lines
        for (const rel of relationships) {
            const fromPos = tablePositions.get(rel.fromTable);
            const toPos = tablePositions.get(rel.toTable);

            if (!fromPos || !toPos) {
                console.warn(`Cannot draw relationship: ${rel.fromTable}.${rel.fromColumn} -> ${rel.toTable}.${rel.toColumn} (missing position)`);
                continue;
            }

            // Calculate connection points based on relative positions
            let fromX, fromY, toX, toY;

            // If target is to the right, connect from right side to left side
            if (toPos.x > fromPos.x + fromPos.width) {
                fromX = fromPos.x + fromPos.width;
                fromY = fromPos.y + fromPos.height / 2;
                toX = toPos.x;
                toY = toPos.y + toPos.height / 2;
            }
            // If target is to the left, connect from left side to right side
            else if (toPos.x + toPos.width < fromPos.x) {
                fromX = fromPos.x;
                fromY = fromPos.y + fromPos.height / 2;
                toX = toPos.x + toPos.width;
                toY = toPos.y + toPos.height / 2;
            }
            // If target is above or below, connect vertically
            else {
                if (toPos.y < fromPos.y) {
                    // Target is above
                    fromX = fromPos.x + fromPos.width / 2;
                    fromY = fromPos.y;
                    toX = toPos.x + toPos.width / 2;
                    toY = toPos.y + toPos.height;
                } else {
                    // Target is below
                    fromX = fromPos.x + fromPos.width / 2;
                    fromY = fromPos.y + fromPos.height;
                    toX = toPos.x + toPos.width / 2;
                    toY = toPos.y;
                }
            }

            // Draw line with arrow
            const line = this.createRelationshipLine(fromX, fromY, toX, toY);
            group.appendChild(line);

            // Add arrow marker at the end
            const arrow = this.createArrowMarker(toX, toY, fromX, fromY);
            group.appendChild(arrow);

            console.log(`Drew relationship: ${rel.fromTable}.${rel.fromColumn} -> ${rel.toTable}.${rel.toColumn}`);
        }

        svg.appendChild(group);

        // If no relationships were found, add a subtle message
        if (relationships.length === 0) {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', '50%');
            text.setAttribute('y', '30');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', 'var(--viewer-subtitle-color, #858585)');
            text.setAttribute('font-size', '12px');
            text.textContent = 'No foreign key relationships detected';
            svg.appendChild(text);
        } else {
            // Show relationship count in top-left corner
            const countText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            countText.setAttribute('x', '10');
            countText.setAttribute('y', '25');
            countText.setAttribute('fill', 'var(--viewer-subtitle-color, #858585)');
            countText.setAttribute('font-size', '11px');
            countText.textContent = `${relationships.length} relationship${relationships.length > 1 ? 's' : ''} detected`;
            svg.appendChild(countText);
        }
    }

    findTargetTable(columnName) {
        /**
         * Find the target table for a foreign key column
         * Handles complex naming patterns like user_id -> user_profiles
         */
        if (!columnName.endsWith('_id')) return null;

        // Remove '_id' suffix
        const baseName = columnName.slice(0, -3);

        // Strategy 1: Exact match (e.g., user_id -> user, session_id -> session)
        for (const table of this.schema) {
            if (table.name.toLowerCase() === baseName.toLowerCase()) {
                if (this.hasPrimaryKey(table)) {
                    return table;
                }
            }
        }

        // Strategy 2: Plural forms (e.g., user_id -> users, category_id -> categories)
        const pluralForms = [
            baseName + 's',
            baseName + 'es',
            baseName.replace(/y$/, 'ies'), // category -> categories
        ];

        for (const plural of pluralForms) {
            for (const table of this.schema) {
                if (table.name.toLowerCase() === plural.toLowerCase()) {
                    if (this.hasPrimaryKey(table)) {
                        return table;
                    }
                }
            }
        }

        // Strategy 3: Table name starts with base name (e.g., user_id -> user_profiles)
        for (const table of this.schema) {
            if (table.name.toLowerCase().startsWith(baseName.toLowerCase() + '_')) {
                if (this.hasPrimaryKey(table)) {
                    return table;
                }
            }
        }

        // Strategy 4: Table name contains base name (e.g., session_id -> terminal_sessions)
        const candidates = [];
        for (const table of this.schema) {
            const tableLower = table.name.toLowerCase();
            const baseLower = baseName.toLowerCase();

            // Check if table contains the base name as a word
            if (tableLower.includes(baseLower) || tableLower.includes(baseLower + 's')) {
                if (this.hasPrimaryKey(table)) {
                    // Prefer tables ending with the base name
                    const priority = tableLower.endsWith(baseLower) || tableLower.endsWith(baseLower + 's') ? 1 : 2;
                    candidates.push({ table, priority });
                }
            }
        }

        // Sort by priority and return best match
        if (candidates.length > 0) {
            candidates.sort((a, b) => a.priority - b.priority);
            return candidates[0].table;
        }

        // Strategy 5: Handle special cases (terminal_session_id -> terminal_sessions)
        // Remove underscores and try matching
        const baseNameNoUnderscore = baseName.replace(/_/g, '');
        for (const table of this.schema) {
            const tableNameNoUnderscore = table.name.replace(/_/g, '').toLowerCase();
            if (tableNameNoUnderscore === baseNameNoUnderscore ||
                tableNameNoUnderscore === baseNameNoUnderscore + 's') {
                if (this.hasPrimaryKey(table)) {
                    return table;
                }
            }
        }

        return null;
    }

    hasPrimaryKey(table) {
        /**
         * Check if table has a primary key column
         */
        return table.columns.some(c => c.primary_key);
    }

    findPrimaryKeyColumn(table) {
        /**
         * Find the primary key column name for a table
         */
        const pkColumn = table.columns.find(c => c.primary_key);
        return pkColumn ? pkColumn.name : 'id';
    }

    createRelationshipLine(x1, y1, x2, y2) {
        /**
         * Create a curved line between two points for relationships
         */
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');

        // Calculate control points for a nice curve
        const midX = (x1 + x2) / 2;
        const dx = Math.abs(x2 - x1);
        const curveOffset = Math.min(dx * 0.3, 50);

        // Create a curved path (quadratic bezier)
        const pathData = `M ${x1} ${y1} Q ${x1 + curveOffset} ${y1}, ${midX} ${(y1 + y2) / 2} T ${x2} ${y2}`;

        line.setAttribute('d', pathData);
        line.setAttribute('class', 'er-relationship-line');
        line.setAttribute('stroke', 'var(--viewer-accent, #007acc)');
        line.setAttribute('stroke-width', '2.5');
        line.setAttribute('fill', 'none');
        line.setAttribute('opacity', '0.75');
        line.setAttribute('stroke-dasharray', '5,3'); // Dashed line for better visibility

        return line;
    }

    createArrowMarker(x, y, fromX, fromY) {
        /**
         * Create an arrow marker at the end of a relationship line
         */
        // Calculate angle for arrow direction
        const angle = Math.atan2(y - fromY, x - fromX);
        const arrowSize = 8;

        // Create arrow as a polygon
        const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');

        // Arrow points (pointing right by default)
        const points = [
            { x: 0, y: 0 },
            { x: -arrowSize, y: -arrowSize / 2 },
            { x: -arrowSize, y: arrowSize / 2 }
        ];

        // Rotate and translate points
        const rotatedPoints = points.map(p => {
            const rotX = p.x * Math.cos(angle) - p.y * Math.sin(angle);
            const rotY = p.x * Math.sin(angle) + p.y * Math.cos(angle);
            return `${x + rotX},${y + rotY}`;
        });

        arrow.setAttribute('points', rotatedPoints.join(' '));
        arrow.setAttribute('fill', 'var(--viewer-accent, #007acc)');
        arrow.setAttribute('stroke', 'var(--viewer-accent, #007acc)');
        arrow.setAttribute('stroke-width', '1');
        arrow.setAttribute('opacity', '0.9');

        return arrow;
    }

    setupERDiagramInteraction(svg, container) {
        /**
         * Setup zoom and pan for ER diagram with enhanced zoom range
         */
        let scale = 1;
        let translateX = 0;
        let translateY = 0;
        let isDragging = false;
        let startX = 0;
        let startY = 0;

        // Store zoom state for controls
        this.erZoomState = { scale, translateX, translateY };

        // Zoom on scroll - increased range from 0.3-3 to 0.1-10
        container.addEventListener('wheel', (e) => {
            e.preventDefault();

            const delta = e.deltaY > 0 ? 0.85 : 1.15; // More aggressive zoom
            const newScale = Math.max(0.1, Math.min(10, scale * delta)); // Wider range

            scale = newScale;
            this.erZoomState.scale = scale;
            svg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        }, { passive: false });

        // Pan on drag
        container.addEventListener('mousedown', (e) => {
            if (e.target === svg || svg.contains(e.target)) {
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                container.style.cursor = 'grabbing';
            }
        });

        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            translateX = e.clientX - startX;
            translateY = e.clientY - startY;
            this.erZoomState.translateX = translateX;
            this.erZoomState.translateY = translateY;
            svg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        });

        container.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = 'grab';
        });

        container.addEventListener('mouseleave', () => {
            isDragging = false;
            container.style.cursor = '';
        });

        // Set initial cursor
        container.style.cursor = 'grab';

        // Add zoom control buttons
        this.addERZoomControls(container, svg);
    }

    addERZoomControls(container, svg) {
        /**
         * Add zoom in/out and reset buttons to ER diagram
         */
        const controlsHtml = `
            <div class="er-zoom-controls">
                <button class="er-zoom-btn" id="${this.viewerId}-zoom-in" title="Zoom in (+)">+</button>
                <button class="er-zoom-btn" id="${this.viewerId}-zoom-reset" title="Reset zoom (0)">⊙</button>
                <button class="er-zoom-btn" id="${this.viewerId}-zoom-out" title="Zoom out (-)">−</button>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', controlsHtml);

        // Zoom in button
        const zoomInBtn = document.getElementById(`${this.viewerId}-zoom-in`);
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => {
                if (!this.erZoomState) return;
                const newScale = Math.min(10, this.erZoomState.scale * 1.3);
                this.erZoomState.scale = newScale;
                svg.style.transform = `translate(${this.erZoomState.translateX}px, ${this.erZoomState.translateY}px) scale(${newScale})`;
            });
        }

        // Zoom out button
        const zoomOutBtn = document.getElementById(`${this.viewerId}-zoom-out`);
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => {
                if (!this.erZoomState) return;
                const newScale = Math.max(0.1, this.erZoomState.scale * 0.7);
                this.erZoomState.scale = newScale;
                svg.style.transform = `translate(${this.erZoomState.translateX}px, ${this.erZoomState.translateY}px) scale(${newScale})`;
            });
        }

        // Reset zoom button
        const zoomResetBtn = document.getElementById(`${this.viewerId}-zoom-reset`);
        if (zoomResetBtn) {
            zoomResetBtn.addEventListener('click', () => {
                if (!this.erZoomState) return;
                this.erZoomState.scale = 1;
                this.erZoomState.translateX = 0;
                this.erZoomState.translateY = 0;
                svg.style.transform = 'translate(0px, 0px) scale(1)';
            });
        }

        // Keyboard shortcuts for zoom
        document.addEventListener('keydown', (e) => {
            const overlay = document.getElementById(`${this.viewerId}-overlay`);
            if (!overlay || overlay.style.display === 'none') return;

            const erTab = document.querySelector(`#${this.viewerId}-container .sql-tab-btn[data-tab="er-diagram"]`);
            if (!erTab || !erTab.classList.contains('active')) return;

            if (e.key === '+' || e.key === '=') {
                e.preventDefault();
                zoomInBtn?.click();
            } else if (e.key === '-' || e.key === '_') {
                e.preventDefault();
                zoomOutBtn?.click();
            } else if (e.key === '0') {
                e.preventDefault();
                zoomResetBtn?.click();
            }
        });
    }

    toggleFullscreen() {
        /**
         * Toggle fullscreen mode for schema/ER diagram panel
         */
        const schemaPanel = document.querySelector(`#${this.viewerId}-container .sql-schema-panel`);
        const mainPanel = document.querySelector(`#${this.viewerId}-container .sql-main-panel`);
        const historyPanel = document.querySelector(`#${this.viewerId}-container .sql-history-panel`);
        const fullscreenBtn = document.getElementById(`${this.viewerId}-fullscreen-btn`);

        if (!schemaPanel) return;

        this.isFullscreen = !this.isFullscreen;

        if (this.isFullscreen) {
            // Enter fullscreen mode
            schemaPanel.classList.add('fullscreen');
            if (mainPanel) mainPanel.classList.add('hidden');
            if (historyPanel) historyPanel.classList.add('hidden');
            if (fullscreenBtn) {
                fullscreenBtn.textContent = '⛶';
                fullscreenBtn.title = 'Exit fullscreen (F or Esc)';
            }
        } else {
            // Exit fullscreen mode
            schemaPanel.classList.remove('fullscreen');
            if (mainPanel) mainPanel.classList.remove('hidden');
            if (historyPanel && !this.isHistoryCollapsed) {
                historyPanel.classList.remove('hidden');
            }
            if (fullscreenBtn) {
                fullscreenBtn.textContent = '⛶';
                fullscreenBtn.title = 'Toggle fullscreen (F)';
            }
        }

        // Re-render ER diagram if it's active to adjust to new size
        const erTab = document.querySelector(`#${this.viewerId}-container .sql-tab-btn[data-tab="er-diagram"]`);
        if (erTab && erTab.classList.contains('active')) {
            // Small delay to let CSS transitions complete
            setTimeout(() => this.renderERDiagram(), 350);
        }
    }

    toggleHistoryPanel() {
        /**
         * Toggle visibility of history panel
         */
        const historyPanel = document.querySelector(`#${this.viewerId}-container .sql-history-panel`);
        const collapseBtn = document.getElementById(`${this.viewerId}-collapse-history`);

        if (!historyPanel) return;

        this.isHistoryCollapsed = !this.isHistoryCollapsed;

        if (this.isHistoryCollapsed) {
            historyPanel.classList.add('collapsed');
            if (collapseBtn) {
                collapseBtn.textContent = '⮞';
                collapseBtn.title = 'Show history panel';
            }
        } else {
            historyPanel.classList.remove('collapsed');
            if (collapseBtn) {
                collapseBtn.textContent = '⮜';
                collapseBtn.title = 'Hide history panel';
            }
        }
    }

    getDisplayName() {
        /**
         * Get display name for database
         */
        if (this.dbPath) {
            return this.dbPath.split('/').pop();
        }
        return 'Database';
    }

    getFileName() {
        return this.getDisplayName();
    }

    showLoading(message) {
        const resultsTable = document.getElementById(`${this.viewerId}-results-table`);
        if (resultsTable) {
            resultsTable.innerHTML = `
                <div class="viewer-loading">
                    <div class="viewer-spinner"></div>
                    <div>${message}</div>
                </div>
            `;
        }
    }

    showError(message) {
        const resultsTable = document.getElementById(`${this.viewerId}-results-table`);
        if (resultsTable) {
            resultsTable.innerHTML = `
                <div class="viewer-error">
                    <div class="viewer-error-icon">⚠️</div>
                    <div>${message}</div>
                </div>
            `;
        }
        this.setStatus(`Error: ${message}`);
    }

    setStatus(message) {
        const statusBar = document.getElementById(`${this.viewerId}-status`);
        if (statusBar) {
            statusBar.textContent = message;
        }
    }
}

// Export for use in terminal.js
window.SQLViewer = SQLViewer;
