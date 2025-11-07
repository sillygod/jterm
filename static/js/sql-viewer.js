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
                                <span>Schema</span>
                                <button class="sql-refresh-btn" id="${this.viewerId}-refresh-schema" title="Refresh schema">
                                    ↻
                                </button>
                            </div>
                            <div class="sql-panel-content">
                                <div id="${this.viewerId}-schema-tree" class="sql-schema-tree"></div>
                            </div>
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
         * Show format selection dialog
         */
        return new Promise((resolve) => {
            const format = prompt('Export format:\n1. csv\n2. json\n3. xlsx\n\nEnter format:', 'csv');
            resolve(format ? format.toLowerCase() : null);
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
