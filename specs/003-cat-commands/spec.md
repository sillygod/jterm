# Feature Specification: Web-Enhanced Cat Commands

**Feature Branch**: `001-cat-commands`
**Created**: 2025-11-04
**Status**: Draft
**Input**: User description: "Implement four new web-enhanced terminal commands: logcat, certcat, sqlcat, and curlcat. Each follows the existing OSC sequence architecture pattern used by imgcat, vidcat, etc."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Structured Logs (Priority: P1)

As a developer debugging an application, I need to view and analyze log files with proper formatting, filtering, and search capabilities so I can quickly identify and diagnose issues without switching to external tools.

**Why this priority**: Core functionality that provides immediate value. Log viewing is the most common debugging task and delivers standalone value even without other cat commands.

**Independent Test**: Can be fully tested by running `logcat app.log` with a sample JSON log file and verifying that logs are displayed in a structured, filterable view. Delivers value by making logs readable and searchable.

**Acceptance Scenarios**:

1. **Given** a JSON log file exists, **When** user runs `logcat app.log`, **Then** logs are displayed in a split-view interface with structured formatting
2. **Given** logs are displayed, **When** user applies level filter (ERROR, WARN), **Then** only matching log entries are shown
3. **Given** logs are displayed, **When** user searches with regex pattern, **Then** matching entries are highlighted and shown
4. **Given** a log file is being written to, **When** user runs `logcat app.log --follow`, **Then** new log entries appear in real-time
5. **Given** filtered logs are displayed, **When** user clicks export, **Then** visible entries are saved to a file

---

### User Story 2 - Inspect SSL Certificates (Priority: P2)

As a system administrator or security engineer, I need to inspect SSL certificates from remote endpoints or local files to verify validity, expiration dates, and chain of trust so I can ensure secure communications and proactively address certificate issues.

**Why this priority**: Important security tool but less frequently used than log viewing. Provides independent value for certificate management and troubleshooting.

**Independent Test**: Can be fully tested by running `certcat https://example.com` and verifying that certificate details, chain visualization, and trust status are correctly displayed. Delivers value by making certificate inspection visual and accessible.

**Acceptance Scenarios**:

1. **Given** a remote HTTPS endpoint, **When** user runs `certcat https://example.com`, **Then** certificate details including subject, issuer, validity period, and SAN are displayed
2. **Given** a local PEM file, **When** user runs `certcat cert.pem`, **Then** certificate information is extracted and displayed
3. **Given** a certificate chain exists, **When** user views certificate, **Then** full chain is visualized as a tree diagram with parent-child relationships
4. **Given** a certificate is expiring soon, **When** certificate is displayed, **Then** expiry warning is prominently shown
5. **Given** two certificates, **When** user runs `certcat site1.com site2.com --compare`, **Then** differences are highlighted side-by-side

---

### User Story 3 - Query Databases Interactively (Priority: P2)

As a data analyst or developer, I need to execute SQL queries and visualize results directly in the terminal so I can explore databases and extract insights without leaving my development environment.

**Why this priority**: Equal priority with certcat as both serve specific but important use cases. Provides standalone value for database exploration and analysis.

**Independent Test**: Can be fully tested by running `sqlcat --db test.db --query "SELECT * FROM users"` against a SQLite database and verifying that results are displayed in a table with sorting and export options. Delivers value by making database querying accessible and visual.

**Acceptance Scenarios**:

1. **Given** a SQLite database file, **When** user runs `sqlcat --db data.db`, **Then** interactive mode opens with schema explorer
2. **Given** a query is entered, **When** user executes query, **Then** results are displayed in a sortable, filterable table
3. **Given** query results contain numeric data, **When** user selects chart mode, **Then** data is visualized as a chart (bar, line, or pie)
4. **Given** query results are displayed, **When** user clicks export, **Then** results are saved as CSV, JSON, or Excel
5. **Given** a PostgreSQL connection string, **When** user runs `sqlcat --db postgresql://...`, **Then** connection is established and queries can be executed

---

### User Story 4 - Test HTTP APIs (Priority: P3)

As a developer or QA engineer, I need to execute HTTP requests and analyze responses with detailed timing and formatting so I can test APIs, debug integration issues, and understand request/response flows.

**Why this priority**: Valuable but lowest priority as external tools like Postman/Insomnia exist. Still provides value through terminal integration and environment variable management.

**Independent Test**: Can be fully tested by running `curlcat https://api.example.com/users` and verifying that the request is executed with response details, headers, timing breakdown, and formatting displayed. Delivers value by making HTTP testing integrated with terminal workflow.

**Acceptance Scenarios**:

1. **Given** an API endpoint, **When** user runs `curlcat https://api.example.com/users`, **Then** GET request is executed and response is displayed with formatting
2. **Given** response is displayed, **When** user views timing tab, **Then** DNS, TCP, TLS, and transfer timings are shown in a waterfall chart
3. **Given** a POST request with data, **When** user runs `curlcat https://api.example.com/users -X POST -d '...'`, **Then** request is sent and response is captured
4. **Given** environment variables are defined, **When** user runs `curlcat {{BASE_URL}}/users`, **Then** variables are substituted and request is executed
5. **Given** request history exists, **When** user runs `curlcat --history`, **Then** previous requests are listed and can be replayed

---

### Edge Cases

- What happens when a log file exceeds 50MB or 100k lines? (Performance degradation, memory limits, pagination)
- How does the system handle corrupted or malformed certificate files? (Error messages, partial information display)
- What happens when a database connection fails or times out? (Retry logic, clear error messages, connection status)
- How does the system handle non-standard log formats that don't match JSON or Apache/Nginx patterns? (Raw text display, format detection failure messages)
- What happens when following a log file that is rotated? (Detect rotation, re-open file, continue streaming)
- How are very large SQL result sets handled? (Virtual scrolling, row limits, streaming responses)
- What happens when an HTTP request hangs or times out? (Configurable timeout, cancellation, partial response display)
- How are binary responses handled in curlcat? (Hex display, save to file option, content-type detection)
- What happens when private keys are provided to certcat? (Security warning, metadata-only display, never show key contents)

## Requirements *(mandatory)*

### Functional Requirements

#### LOGCAT Requirements

- **FR-001**: System MUST parse and display JSON logs with key-value expansion
- **FR-002**: System MUST parse and display Apache/Nginx logs (combined, common, error formats)
- **FR-003**: System MUST auto-detect log format when not specified
- **FR-004**: System MUST support real-time log streaming with `--follow` flag
- **FR-005**: System MUST filter logs by level (ERROR, WARN, INFO, DEBUG, TRACE)
- **FR-006**: System MUST filter logs by timestamp range with `--since` and `--until` options
- **FR-007**: System MUST support full-text search with regex patterns
- **FR-008**: System MUST highlight search matches and syntax-highlight log levels
- **FR-009**: System MUST display logs in split-view (list + detail panel)
- **FR-010**: System MUST allow collapsing/expanding stack traces
- **FR-011**: System MUST allow collapsing/expanding JSON fields
- **FR-012**: System MUST show time-series visualization of log levels
- **FR-013**: System MUST provide quick filters sidebar (level, source, module)
- **FR-014**: System MUST support exporting filtered results to file
- **FR-015**: System MUST handle log files up to 50MB and 100k+ lines
- **FR-016**: System MUST accept log data from stdin pipe (e.g., `tail -f | logcat`)

#### CERTCAT Requirements

- **FR-017**: System MUST fetch certificates from remote HTTPS endpoints
- **FR-018**: System MUST parse local PEM and CRT certificate files
- **FR-019**: System MUST display certificate details (subject, issuer, validity dates, public key info)
- **FR-020**: System MUST visualize full certificate chains as tree diagrams
- **FR-021**: System MUST validate certificate chains against system trust store
- **FR-022**: System MUST display Subject Alternative Names (SAN)
- **FR-023**: System MUST highlight certificates that are expired or expiring within 30 days
- **FR-024**: System MUST show public key details (algorithm, size, fingerprint)
- **FR-025**: System MUST display trust status with visual badges
- **FR-026**: System MUST support comparing two certificates side-by-side
- **FR-027**: System MUST warn about self-signed certificates
- **FR-028**: System MUST export certificates in PEM, DER, and text formats
- **FR-029**: System MUST inspect private key metadata without displaying key contents
- **FR-030**: System MUST never display private key contents (security requirement)

#### SQLCAT Requirements

- **FR-031**: System MUST connect to SQLite databases from file paths
- **FR-032**: System MUST connect to PostgreSQL databases via connection strings
- **FR-033**: System MUST display database schema (tables, columns, indexes)
- **FR-034**: System MUST execute SQL queries and display results
- **FR-035**: System MUST render query results as sortable, filterable tables
- **FR-036**: System MUST render numeric query results as charts (bar, line, pie)
- **FR-037**: System MUST provide syntax highlighting for SQL queries
- **FR-038**: System MUST save query history
- **FR-039**: System MUST allow replaying previous queries
- **FR-040**: System MUST export results as CSV, JSON, and Excel formats
- **FR-041**: System MUST visualize query execution plans (EXPLAIN output)
- **FR-042**: System MUST limit result rows (default 1000, configurable)
- **FR-043**: System MUST operate in read-only mode by default
- **FR-044**: System MUST require explicit `--write` flag for INSERT/UPDATE/DELETE/DDL operations
- **FR-045**: System MUST prompt for passwords when connecting to password-protected databases
- **FR-046**: System MUST prevent SQL injection in query builder
- **FR-047**: System MUST provide visual query builder (no-code option)
- **FR-048**: System MUST show entity-relationship diagram for schema

#### CURLCAT Requirements

- **FR-049**: System MUST execute HTTP requests (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
- **FR-050**: System MUST display request and response details (headers, body, status)
- **FR-051**: System MUST auto-format response bodies (JSON, XML, HTML)
- **FR-052**: System MUST show timing breakdown (DNS, TCP, TLS, transfer phases)
- **FR-053**: System MUST save request history with timestamps
- **FR-054**: System MUST allow replaying previous requests
- **FR-055**: System MUST support environment variables for reusable values (e.g., `{{API_TOKEN}}`)
- **FR-056**: System MUST provide variable substitution in URLs, headers, and body
- **FR-057**: System MUST support Basic, Bearer token, and API key authentication
- **FR-058**: System MUST visualize redirect chains when following redirects
- **FR-059**: System MUST display request waterfall timing diagram
- **FR-060**: System MUST manage cookies (view, edit, delete)
- **FR-061**: System MUST show certificate validation details for HTTPS requests
- **FR-062**: System MUST handle compressed responses (gzip, deflate, brotli)
- **FR-063**: System MUST generate code snippets (curl, fetch, axios, Python requests)
- **FR-064**: System MUST provide searchable, filterable history sidebar
- **FR-065**: System MUST export history as collection file

#### Shared Architecture Requirements

- **FR-066**: All commands MUST use OSC sequence pattern (OSC 1337) to communicate with terminal UI
- **FR-067**: All commands MUST provide bash script wrappers in `bin/` directory
- **FR-068**: All commands MUST provide FastAPI service layer in `src/services/`
- **FR-069**: All commands MUST provide API endpoints in `src/api/`
- **FR-070**: All commands MUST provide frontend JavaScript viewers in `static/js/`
- **FR-071**: All commands MUST provide HTMX templates in `templates/components/`
- **FR-072**: All commands MUST handle errors gracefully with user-friendly messages
- **FR-073**: All commands MUST show loading states during processing
- **FR-074**: All commands MUST support keyboard shortcuts for navigation
- **FR-075**: All commands MUST be responsive and work on all screen sizes
- **FR-076**: All commands MUST match terminal theme (dark/light mode)
- **FR-077**: All commands MUST provide export options in multiple formats

### Key Entities

- **LogEntry**: Represents a single log line with timestamp, level, message, source, stack trace (if applicable), and structured fields (for JSON logs)
- **Certificate**: Represents an X.509 certificate with subject, issuer, validity period, public key, SAN, fingerprint, and chain relationships
- **DatabaseConnection**: Represents a connection to a database with connection string, database type, schema metadata
- **QueryResult**: Represents SQL query results with column definitions, rows, row count, execution time
- **HTTPRequest**: Represents an HTTP request with method, URL, headers, body, authentication, timing metrics
- **HTTPResponse**: Represents an HTTP response with status code, headers, body, timing breakdown, redirect chain
- **EnvironmentVariable**: Represents a reusable variable with name and value for curlcat

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view and filter a 10MB log file within 2 seconds of opening
- **SC-002**: Real-time log streaming displays new entries within 100ms of being written to file
- **SC-003**: Certificate inspection for remote endpoints completes within 3 seconds
- **SC-004**: SQL query results for queries returning up to 10,000 rows display within 2 seconds
- **SC-005**: HTTP request execution and response display complete within 5 seconds (excluding actual request time)
- **SC-006**: All viewer UIs render initial interface within 1 second
- **SC-007**: Users can search through 100k log entries and see results within 1 second
- **SC-008**: System handles files up to 50MB without crashing or significant performance degradation
- **SC-009**: Virtual scrolling maintains smooth performance with datasets of 100k+ rows
- **SC-010**: All export operations complete within 5 seconds for typical datasets (1000-10000 items)
- **SC-011**: Users can complete common tasks (view logs, inspect certificate, query database, test API) without leaving the terminal
- **SC-012**: 90% of users successfully complete primary task on first attempt without external documentation

## Assumptions

- Log files follow standard formats (JSON, Apache/Nginx) or plain text; proprietary binary formats are not supported
- Certificate inspection assumes standard X.509 certificates; proprietary certificate formats are not supported
- SQLite and PostgreSQL are sufficient database engines; other databases (MySQL, Oracle, etc.) are out of scope for initial release
- HTTP request functionality assumes standard HTTP/1.1 and HTTP/2; HTTP/3 support is deferred to future releases
- Users have appropriate system permissions to read log files, certificate files, and connect to databases
- Terminal width is at least 80 characters for proper UI rendering
- Modern browsers with JavaScript ES2022 support for frontend viewers
- WebSocket connection is available for real-time features (log streaming)
- System trust store is available for certificate validation (standard on modern OS)
- Database connections use standard connection strings (no custom authentication mechanisms)
- Export file formats are standard CSV, JSON, Excel (XLSX), PEM, DER
- Performance targets assume modern hardware (4+ core CPU, 8GB+ RAM)
- Certificate expiry warnings default to 30-day threshold (industry standard)
- SQL query timeout defaults to 30 seconds (configurable)
- HTTP request timeout defaults to 30 seconds (configurable)
- Environment variables are stored in memory only, not persisted across sessions (for security)
- Request history is stored locally in browser storage with 30-day retention
- Query history is stored locally in browser storage with 30-day retention

## Security Considerations

- **Private Key Protection**: certcat MUST never display private key contents, only metadata (algorithm, size). Display security warning when private keys are provided.
- **SQL Injection Prevention**: sqlcat MUST sanitize all user inputs in query builder and parameterize queries to prevent SQL injection attacks.
- **Credential Management**: Database passwords and API tokens MUST NOT be stored in browser storage or logs. Connection strings should be masked in history.
- **Read-Only Default**: sqlcat MUST operate in read-only mode by default to prevent accidental data modifications. Write operations require explicit `--write` flag.
- **HTTPS Validation**: curlcat MUST validate HTTPS certificates by default and warn users when connecting to endpoints with invalid certificates.
- **HTML Sandboxing**: When displaying HTML responses in curlcat, content MUST be sandboxed to prevent XSS attacks.
- **File Path Validation**: All commands MUST validate file paths to prevent directory traversal attacks.
- **Environment Variable Isolation**: curlcat environment variables MUST be scoped per-session and cleared on session end to prevent credential leakage.
- **Certificate Chain Validation**: certcat MUST validate full certificate chains against system trust store and clearly indicate trust status.
- **Log Sanitization**: logcat MUST sanitize displayed logs to prevent terminal injection attacks via ANSI escape sequences in log data.

## Dependencies

- Existing OSC sequence handler in `terminal.js` (used by imgcat, vidcat, bookcat)
- Existing FastAPI application structure in `src/`
- Existing HTMX template system in `templates/`
- Python libraries: aiofiles (file I/O), cryptography (certificate parsing), aiosqlite (SQLite), asyncpg (PostgreSQL), httpx (HTTP client)
- JavaScript libraries: xterm.js (terminal integration), Chart.js (data visualization), Monaco Editor or CodeMirror (SQL editor), Prism.js (syntax highlighting)
- System trust store (for certificate validation)
- WebSocket support (for real-time log streaming)

## Out of Scope

- Support for log formats beyond JSON, Apache/Nginx, and plain text (e.g., proprietary binary formats)
- Support for databases beyond SQLite and PostgreSQL (MySQL, Oracle, MongoDB, etc.)
- GraphQL API testing (only REST/HTTP)
- WebSocket request testing in curlcat (only HTTP/HTTPS)
- Certificate generation or modification (read-only inspection only)
- Log aggregation from multiple sources (single file or stdin only)
- Advanced SQL features like stored procedures, triggers, or database-specific extensions
- Integration with external secret management systems (Vault, AWS Secrets Manager)
- Multi-user collaboration features (shared queries, shared requests)
- Advanced chart types beyond bar, line, and pie charts
- PDF or image export of charts and visualizations
- Plugin system for custom log parsers or database drivers
- Mobile responsive design (desktop terminal focused)
- Offline mode (requires active server connection)
