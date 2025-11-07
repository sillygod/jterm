# Frontend Dependencies for jterm Cat Commands

This directory contains third-party JavaScript libraries used by the web-enhanced cat commands (logcat, certcat, sqlcat, curlcat).

## Libraries Included

### Chart.js v4.4.0
- **File**: `chart.js/chart.min.js`
- **Purpose**: Data visualization for SQL query results (bar, line, pie charts)
- **License**: MIT
- **Documentation**: https://www.chartjs.org/docs/

### D3.js v7
- **File**: `d3/d3.min.js`
- **Purpose**: Certificate chain tree visualization
- **License**: BSD 3-Clause
- **Documentation**: https://d3js.org/

### Prism.js v1.29.0
- **Files**:
  - `prism/prism.css` - Tomorrow theme
  - `prism/prism.js` - Core library
  - `prism/prism-sql.js` - SQL syntax highlighting
  - `prism/prism-json.js` - JSON syntax highlighting
- **Purpose**: Syntax highlighting for logs, SQL queries, and HTTP responses
- **License**: MIT
- **Documentation**: https://prismjs.com/

### CodeMirror 6
- **Files**: `codemirror/setup.js` - ES module setup for CDN imports
- **Purpose**: SQL query editor with syntax highlighting and autocomplete
- **License**: MIT
- **Documentation**: https://codemirror.net/

## Usage

These dependencies are loaded by the respective viewer components:

- **Log Viewer**: Prism.js for JSON log syntax highlighting
- **Certificate Viewer**: D3.js for certificate chain tree visualization
- **SQL Viewer**: CodeMirror 6 for query editing, Chart.js for result visualization
- **HTTP Viewer**: Prism.js for response formatting

## CDN Fallback

If local files are not available, the components will fall back to CDN versions. The CodeMirror setup uses esm.sh CDN for ES module compatibility.

## Updates

To update these libraries:

1. Check for new versions on their respective CDN sources
2. Download updated files
3. Update version numbers in this README
4. Test with all cat command viewers

## Bundle Sizes

- Chart.js: ~200KB
- D3.js: ~273KB
- Prism.js: ~20KB (core + languages + theme)
- CodeMirror 6: Loaded from CDN (ES modules)

**Total local storage**: ~493KB