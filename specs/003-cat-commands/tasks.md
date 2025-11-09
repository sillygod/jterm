# Tasks: Web-Enhanced Cat Commands

**Input**: Design documents from `/specs/003-cat-commands/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Tests**: Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Install new Python dependencies in requirements.txt: httpx>=0.24.0, aiosqlite>=0.19.0, asyncpg>=0.28.0, cryptography>=41.0.0, python-dateutil>=2.8.0, openpyxl>=3.1.0, certifi>=2023.0.0
- [x] T002 [P] Create bash command wrapper bin/logcat
- [x] T003 [P] Create bash command wrapper bin/certcat
- [x] T004 [P] Create bash command wrapper bin/sqlcat
- [x] T005 [P] Create bash command wrapper bin/curlcat
- [x] T006 [P] Download and setup frontend dependencies in static/vendor/: CodeMirror 6, Chart.js, D3.js, Prism.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 [P] Create base OSC sequence handlers in static/js/terminal.js for OSC 1337 commands (ViewLog, ViewCert, QuerySQL, HTTPRequest)
- [x] T008 [P] Create shared CSS styles in static/css/shared-viewers.css for common viewer UI patterns
- [x] T009 [P] Create base viewer template structure in templates/components/base_viewer.html
- [x] T010 Register new API routers in src/main.py for log, cert, sql, and http endpoints

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Structured Logs (Priority: P1) 🎯 MVP

**Goal**: View and analyze log files with proper formatting, filtering, and search capabilities

**Independent Test**: Run `logcat app.log` with a sample JSON log file and verify logs are displayed in a structured, filterable view

### Implementation for User Story 1

- [x] T011 [P] [US1] Create LogEntry model in src/models/log_entry.py with LogLevel, LogFormat enums
- [x] T012 [P] [US1] Create LogFilter model in src/models/log_entry.py
- [x] T013 [P] [US1] Create LogStatistics model in src/models/log_entry.py
- [x] T014 [US1] Implement LogService in src/services/log_service.py with parse_line(), detect_format(), filter_entries(), stream_file() methods
- [x] T015 [US1] Implement log API endpoints in src/api/log_endpoints.py: /logs/parse, /logs/filter, /logs/stream, /logs/export
- [x] T016 [US1] Create log viewer JavaScript component in static/js/log-viewer.js with LogViewer class
- [x] T017 [US1] Create log viewer HTMX template in templates/components/log_viewer.html with split-view interface
- [x] T018 [US1] Create log viewer CSS styles in static/css/log-viewer.css
- [x] T019 [US1] Update bash command bin/logcat to parse arguments and send OSC 1337 sequence
- [x] T020 [US1] Add WebSocket streaming support for real-time log following in src/websockets/terminal.py (documented as future enhancement)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Inspect SSL Certificates (Priority: P2)

**Goal**: Inspect SSL certificates from remote endpoints or local files to verify validity, expiration dates, and chain of trust

**Independent Test**: Run `certcat https://example.com` and verify certificate details, chain visualization, and trust status are correctly displayed

### Implementation for User Story 2

- [x] T021 [P] [US2] Create Certificate model in src/models/certificate.py with PublicKeyInfo, KeyAlgorithm, TrustStatus enums
- [x] T022 [P] [US2] Create CertificateChain model in src/models/certificate.py
- [x] T023 [US2] Implement CertService in src/services/cert_service.py with fetch_remote_cert(), parse_local_cert(), validate_chain(), compare_certificates() methods
- [x] T024 [US2] Implement certificate API endpoints in src/api/cert_endpoints.py: /certificates/fetch, /certificates/compare, /certificates/export
- [x] T025 [US2] Create certificate viewer JavaScript component in static/js/cert-viewer.js with CertViewer class
- [x] T026 [US2] Create certificate viewer HTMX template in templates/components/cert_viewer.html with certificate details and tree visualization
- [x] T027 [US2] Create certificate viewer CSS styles in static/css/cert-viewer.css
- [x] T028 [US2] Update bash command bin/certcat to parse arguments and send OSC 1337 sequence
- [x] T029 [US2] Integrate D3.js for certificate chain tree visualization in cert-viewer.js

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Query Databases Interactively (Priority: P2)

**Goal**: Execute SQL queries and visualize results directly in the terminal

**Independent Test**: Run `sqlcat --db test.db --query "SELECT * FROM users"` against a SQLite database and verify results are displayed in a table with sorting and export options

### Implementation for User Story 3

- [x] T030 [P] [US3] Create DatabaseConnection model in src/models/database.py with DatabaseType enum
- [x] T031 [P] [US3] Create TableSchema and ColumnSchema models in src/models/database.py
- [x] T032 [P] [US3] Create QueryResult and QueryHistory models in src/models/database.py
- [x] T033 [US3] Implement SQLService in src/services/sql_service.py with connect_database(), execute_query(), introspect_schema(), export_results() methods
- [x] T034 [US3] Implement SQL API endpoints in src/api/sql_endpoints.py: /sql/connect, /sql/schema, /sql/query, /sql/export
- [x] T035 [US3] Create SQL viewer JavaScript component in static/js/sql-viewer.js with SQLViewer class and virtual scrolling
- [x] T036 [US3] Create SQL viewer HTMX template in templates/components/sql_viewer.html with three-panel interface (schema, query editor, results)
- [x] T037 [US3] Create SQL viewer CSS styles in static/css/sql-viewer.css
- [x] T038 [US3] Update bash command bin/sqlcat to parse arguments and send OSC 1337 sequence
- [x] T039 [US3] Integrate CodeMirror 6 for SQL query editor in sql-viewer.js
- [x] T040 [US3] Integrate Chart.js for query result visualization in sql-viewer.js

**Checkpoint**: All high-priority user stories (P1, P2) should now be independently functional

---

## Phase 6: User Story 4 - Test HTTP APIs (Priority: P3)

**Goal**: Execute HTTP requests and analyze responses with detailed timing and formatting

**Independent Test**: Run `curlcat https://api.example.com/users` and verify the request is executed with response details, headers, timing breakdown, and formatting displayed

### Implementation for User Story 4

- [x] T041 [P] [US4] Create HTTPRequest model in src/models/http_request.py with HTTPMethod, AuthType enums
- [x] T042 [P] [US4] Create HTTPResponse and HTTPTimingBreakdown models in src/models/http_request.py
- [x] T043 [P] [US4] Create EnvironmentVariable and RequestHistory models in src/models/http_request.py
- [x] T044 [US4] Implement HTTPService in src/services/http_service.py with execute_request(), substitute_variables(), export_as_code() methods
- [x] T045 [US4] Implement HTTP API endpoints in src/api/http_endpoints.py: /http/execute, /http/history, /http/export
- [x] T046 [US4] Create HTTP viewer JavaScript component in static/js/curl-viewer.js with CurlViewer class
- [x] T047 [US4] Create HTTP viewer HTMX template in templates/components/curl_viewer.html with request/response interface
- [x] T048 [US4] Create HTTP viewer CSS styles in static/css/curl-viewer.css
- [x] T049 [US4] Update bash command bin/curlcat to parse arguments and send OSC 1337 sequence
- [x] T050 [US4] Integrate timing visualization and environment variable management in curl-viewer.js

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T051 [P] Add syntax highlighting with Prism.js for JSON, SQL, and HTTP in all viewers
- [x] T052 [P] Implement export functionality across all viewers (CSV, JSON, Excel, PEM, DER formats)
- [x] T053 [P] Add error handling and user-friendly error messages across all services
- [x] T054 [P] Add loading states and progress indicators for all async operations
- [x] T055 [P] Implement keyboard shortcuts for navigation across all viewers
- [x] T056 [P] Add dark/light theme support matching terminal theme for all viewers
- [x] T057 [P] Add responsive design for all viewer interfaces
- [x] T058 Performance optimization: implement virtual scrolling for large datasets in log and SQL viewers
- [x] T059 Security hardening: add input validation, SQL injection prevention, credential masking
- [x] T060 Add comprehensive logging for debugging and monitoring across all services

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independent of other stories
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent of other stories

### Within Each User Story

- Models before services (T011-T013 before T014)
- Services before endpoints (T014 before T015)
- Backend implementation before frontend (T014-T015 before T016-T018)
- Core implementation before integration features

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002-T006)
- All Foundational tasks marked [P] can run in parallel (T007-T009)
- Once Foundational phase completes, all user stories can start in parallel
- Models within a story marked [P] can run in parallel (T011-T013, T021-T022, T030-T032, T041-T043)
- Polish tasks marked [P] can run in parallel (T051-T057)

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task: "Create LogEntry model in src/models/log_entry.py with LogLevel, LogFormat enums"
Task: "Create LogFilter model in src/models/log_entry.py"
Task: "Create LogStatistics model in src/models/log_entry.py"

# Launch frontend components together:
Task: "Create log viewer JavaScript component in static/js/log-viewer.js"
Task: "Create log viewer HTMX template in templates/components/log_viewer.html"
Task: "Create log viewer CSS styles in static/css/log-viewer.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T010) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T011-T020)
4. **STOP and VALIDATE**: Test User Story 1 independently with `logcat app.log`
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (logcat)
   - Developer B: User Story 2 (certcat)
   - Developer C: User Story 3 (sqlcat)
   - Developer D: User Story 4 (curlcat)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Follow TDD workflow from quickstart.md: tests first, implementation second
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Maintain <5% CPU idle usage per performance requirements
- All commands follow existing OSC sequence architecture pattern