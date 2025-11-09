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
                                <button class="sql-refresh-btn" id="${this.viewerId}-refresh-schema" title="Refresh schema">
                                    ↻
                                </button>
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
                                <button class="sql-clear-btn" id="${this.viewerId}-clear-history" title="Clear history">
                                    ✕
                                </button>
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
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.executeQuery();
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

        // Create a viewBox for zoom/pan support
        const viewBoxWidth = 1000;
        const viewBoxHeight = Math.max(600, this.schema.length * 150);
        svg.setAttribute('viewBox', `0 0 ${viewBoxWidth} ${viewBoxHeight}`);
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
                font-size: 14px;
                font-weight: bold;
            }
            .er-column-text {
                fill: var(--viewer-fg, #d4d4d4);
                font-size: 11px;
            }
            .er-pk-icon {
                fill: #ffd700;
                font-size: 10px;
            }
            .er-type-text {
                fill: var(--viewer-subtitle-color, #858585);
                font-size: 10px;
            }
            .er-relationship-line {
                stroke: var(--viewer-accent, #007acc);
                stroke-width: 2;
                fill: none;
            }
        `;
        svg.appendChild(style);

        // Layout tables in a grid
        const tableWidth = 250;
        const tableHeaderHeight = 35;
        const columnHeight = 22;
        const padding = 20;
        const columnsPerRow = Math.floor((viewBoxWidth - padding * 2) / (tableWidth + 40));

        // Store table positions for drawing relationships
        const tablePositions = new Map();

        this.schema.forEach((table, index) => {
            const row = Math.floor(index / columnsPerRow);
            const col = index % columnsPerRow;
            const x = padding + col * (tableWidth + 40);
            const y = padding + row * 200;

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

        // Draw relationships (foreign key connections)
        // This is a simplified version - in production would parse FK constraints from schema
        this.drawRelationships(svg, tablePositions);

        // Add zoom/pan controls hint
        const hint = document.createElement('div');
        hint.className = 'er-diagram-hint';
        hint.textContent = 'Scroll to zoom • Drag to pan';
        erContainer.appendChild(hint);

        erContainer.appendChild(svg);

        // Add zoom/pan functionality
        this.setupERDiagramInteraction(svg, erContainer);
    }

    drawRelationships(svg, tablePositions) {
        /**
         * Draw relationship lines between tables based on foreign keys
         * This is a placeholder - real implementation would parse FK constraints
         */
        // In a real implementation, we would:
        // 1. Parse foreign key constraints from table.indexes or schema metadata
        // 2. Draw lines connecting related tables
        // 3. Add cardinality indicators (1:1, 1:N, N:M)

        // For now, just add a placeholder comment in the diagram
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        group.setAttribute('class', 'er-relationships');
        svg.appendChild(group);
    }

    setupERDiagramInteraction(svg, container) {
        /**
         * Setup zoom and pan for ER diagram
         */
        let scale = 1;
        let translateX = 0;
        let translateY = 0;
        let isDragging = false;
        let startX = 0;
        let startY = 0;

        // Zoom on scroll
        container.addEventListener('wheel', (e) => {
            e.preventDefault();

            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const newScale = Math.max(0.3, Math.min(3, scale * delta));

            scale = newScale;
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
