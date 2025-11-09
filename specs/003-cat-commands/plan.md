# Implementation Plan: Web-Enhanced Cat Commands

**Branch**: `003-cat-commands` | **Date**: 2025-11-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-cat-commands/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement four new web-enhanced terminal commands (`logcat`, `certcat`, `sqlcat`, `curlcat`) following the existing OSC sequence architecture pattern. Each command extends jterm's terminal emulator with specialized viewers for logs, certificates, databases, and HTTP requests. All commands use bash wrappers that send OSC 1337 sequences to trigger FastAPI backend services and HTMX frontend viewers. This feature prioritizes log viewing (P1), followed by certificate inspection and SQL querying (P2), with HTTP testing as lowest priority (P3).

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES2022 (frontend)
**Primary Dependencies**: FastAPI, xterm.js, HTMX, WebSockets, Python PTY module
**New Dependencies (Backend)**:
- `httpx>=0.24.0` - Modern async HTTP client (curlcat)
- `sqlalchemy>=2.0.0` - SQL toolkit and ORM (sqlcat) - NEEDS EVALUATION vs aiosqlite direct
- `psycopg2-binary>=2.9.0` - PostgreSQL adapter (sqlcat)
- `cryptography>=41.0.0` - Certificate parsing (certcat)
- `python-dateutil>=2.8.0` - Timestamp parsing (logcat)
- `openpyxl>=3.1.0` - Excel export (sqlcat)

**New Dependencies (Frontend)**:
- `monaco-editor` OR `codemirror` - SQL/code editor - NEEDS EVALUATION
- `chart.js` - Charts for sqlcat visualization
- `d3.js` - Certificate chain tree visualization (certcat)
- `ag-grid-community` OR native HTML tables - NEEDS EVALUATION for performance
- `prism.js` - Syntax highlighting for logs/SQL

**Storage**: SQLite database (existing) + browser localStorage (history/queries) + file system (exports)
**Testing**: pytest (backend), Jest (frontend), Playwright (E2E)
**Target Platform**: Linux/macOS server (backend), Modern browsers (frontend - Chrome, Firefox, Safari)
**Project Type**: Web application (FastAPI + HTMX)
**Performance Goals**:
- Log files: 50MB, 100k+ lines, <2s initial load, <100ms streaming updates
- Certificate fetch: <3s for remote endpoints
- SQL queries: 10k rows <2s, virtual scrolling for 100k+ rows
- HTTP requests: <5s UI response (excluding actual request time)
- UI rendering: <1s initial load for all viewers

**Constraints**:
- Reuse existing OSC sequence architecture (OSC 1337 + 1338)
- Follow existing service pattern (src/services/, src/api/)
- Match terminal theme (dark/light mode support)
- Maintain <5% CPU idle usage (established baseline)
- Browser localStorage for history (30-day retention)
- Memory-efficient log streaming (avoid loading entire file)

**Scale/Scope**:
- 4 new commands: logcat, certcat, sqlcat, curlcat
- ~12 new files: 4 bash scripts, 4 services, 4 API endpoints, 4 JS viewers, 4 HTMX templates
- Estimated 5-8k LOC total (Python + JavaScript)
- Support 2 database engines (SQLite + PostgreSQL)
- Support 3 log formats (JSON, Apache, Nginx)
- Support multiple export formats (CSV, JSON, Excel, PEM, DER)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No formal constitution file exists yet. Applying jterm project conventions from CLAUDE.md:

### Pre-Design Gates

| Gate | Status | Notes |
|------|--------|-------|
| **Service Layer Pattern** | ✅ PASS | Each command gets dedicated service (log_service.py, cert_service.py, etc.) |
| **Single Responsibility** | ✅ PASS | Services separated: parsing, rendering, storage, API endpoints |
| **Test-First (TDD)** | ⚠️ WARN | Must write tests before implementation per CLAUDE.md guidelines |
| **Performance Baseline** | ✅ PASS | Must maintain <5% CPU idle, performance targets defined in spec |
| **Type Hints Required** | ✅ PASS | Python 3.11+ with full type annotations |
| **Code Style (Black/flake8)** | ✅ PASS | Existing formatting standards apply |

### Architectural Alignment

| Principle | Compliant | Justification |
|-----------|-----------|---------------|
| **OSC Sequence Pattern** | ✅ YES | Reuses existing OSC 1337/1338 handlers, follows bookcat/imgcat pattern |
| **Service + API Separation** | ✅ YES | Services in src/services/, endpoints in src/api/ |
| **HTMX Template-Based** | ✅ YES | Minimal JavaScript, HTMX components in templates/components/ |
| **SQLite Storage** | ✅ YES | Reuses existing database, adds localStorage for histories |
| **WebSocket Communication** | ✅ YES | Reuses existing WebSocket infrastructure for log streaming |

### Risk Assessment

**No constitutional violations identified.** This feature extends existing patterns without introducing new architectural paradigms.

## Project Structure

### Documentation (this feature)

```text
specs/003-cat-commands/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: Library evaluations
├── data-model.md        # Phase 1 output: Data entities
├── quickstart.md        # Phase 1 output: Development guide
├── contracts/           # Phase 1 output: API specifications
│   ├── logcat.openapi.yaml
│   ├── certcat.openapi.yaml
│   ├── sqlcat.openapi.yaml
│   └── curlcat.openapi.yaml
├── checklists/
│   └── requirements.md  # Already created during /speckit.specify
└── spec.md              # Feature specification (already exists)
```

### Source Code (repository root)

**Structure Decision**: Web application using existing jterm monorepo structure. This feature adds new services, API endpoints, JavaScript viewers, and HTMX templates following the established pattern used by bookcat, imgcat, vidcat.

```text
bin/                            # ← Bash command wrappers (NEW)
├── logcat                      # ← Log viewer command
├── certcat                     # ← Certificate inspector command
├── sqlcat                      # ← SQL query command
├── curlcat                     # ← HTTP client command
├── bookcat                     # (existing)
├── imgcat                      # (existing)
└── ...

src/
├── models/                     # ← Data models (NEW)
│   ├── log_entry.py            # LogEntry, LogFilter, LogSearch
│   ├── certificate.py          # Certificate, CertificateChain, TrustStatus
│   ├── database.py             # DatabaseConnection, QueryResult, QueryHistory
│   └── http_request.py         # HTTPRequest, HTTPResponse, EnvironmentVariable
│
├── services/                   # ← Business logic (NEW)
│   ├── log_service.py          # Log parsing, filtering, streaming
│   ├── cert_service.py         # Certificate fetching, parsing, validation
│   ├── sql_service.py          # Database connections, query execution
│   ├── http_service.py         # HTTP requests, timing, history
│   ├── ebook_service.py        # (existing)
│   ├── media_service.py        # (existing)
│   └── ...
│
├── api/                        # ← FastAPI endpoints (NEW)
│   ├── log_endpoints.py        # /api/logs/* routes
│   ├── cert_endpoints.py       # /api/certificates/* routes
│   ├── sql_endpoints.py        # /api/sql/* routes
│   └── http_endpoints.py       # /api/http/* routes
│
├── websockets/                 # (existing WebSocket handlers)
│   └── terminal.py             # May need updates for log streaming
│
└── main.py                     # FastAPI app (register new routes)

templates/
├── components/                 # ← HTMX UI components (NEW)
│   ├── log_viewer.html         # Split-view log interface
│   ├── cert_viewer.html        # Certificate details + chain viz
│   ├── sql_viewer.html         # Three-panel SQL interface
│   └── curl_viewer.html        # Request/response interface
│
├── base.html                   # (existing base template)
└── terminal.html               # (existing terminal page)

static/
├── js/                         # ← Frontend JavaScript (NEW)
│   ├── log-viewer.js           # LogViewer class
│   ├── cert-viewer.js          # CertViewer class
│   ├── sql-viewer.js           # SQLViewer class
│   ├── curl-viewer.js          # CurlViewer class
│   └── terminal.js             # ← UPDATE: Register new OSC handlers
│
├── css/
│   ├── log-viewer.css          # ← NEW: Log viewer styles
│   ├── cert-viewer.css         # ← NEW: Certificate viewer styles
│   ├── sql-viewer.css          # ← NEW: SQL viewer styles
│   └── curl-viewer.css         # ← NEW: HTTP viewer styles
│
└── vendor/                     # ← NEW: Third-party libraries
    ├── monaco-editor/          # OR codemirror (TBD in research)
    ├── chart.js/               # Chart visualization
    ├── d3.js/                  # Tree visualization
    └── prism.js/               # Syntax highlighting

tests/
├── contract/                   # ← API contract tests (NEW)
│   ├── test_log_api.py
│   ├── test_cert_api.py
│   ├── test_sql_api.py
│   └── test_http_api.py
│
├── integration/                # ← User story tests (NEW)
│   ├── test_logcat_flow.py     # End-to-end log viewing
│   ├── test_certcat_flow.py    # End-to-end cert inspection
│   ├── test_sqlcat_flow.py     # End-to-end SQL querying
│   └── test_curlcat_flow.py    # End-to-end HTTP testing
│
├── unit/                       # ← Unit tests (NEW)
│   ├── test_log_service.py     # Log parsing, filtering
│   ├── test_cert_service.py    # Certificate parsing, validation
│   ├── test_sql_service.py     # Query execution, schema introspection
│   └── test_http_service.py    # Request execution, timing
│
└── e2e/                        # ← Playwright tests (NEW)
    ├── test_log_viewer_ui.py   # UI interactions
    ├── test_cert_viewer_ui.py  # UI interactions
    ├── test_sql_viewer_ui.py   # UI interactions
    └── test_curl_viewer_ui.py  # UI interactions

requirements.txt                # ← UPDATE: Add new dependencies
```

**Key Files to Modify**:
- `src/main.py` - Register new API routers
- `static/js/terminal.js` - Add OSC handlers for new commands (1337 sequence)
- `requirements.txt` - Add httpx, sqlalchemy, psycopg2-binary, cryptography, python-dateutil, openpyxl

**Estimated File Count**: ~32 new files (4 bash, 4 models, 4 services, 4 API modules, 4 JS viewers, 4 HTMX templates, 4 CSS files, 4 unit test files)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No violations to track. All complexity justified by:
- Reusing existing architectural patterns (OSC sequences, service layer)
- Following established project structure
- No new paradigms or abstractions introduced

---

## Post-Design Constitution Re-Check

**Date**: 2025-11-04 (Phase 1 Complete)

### Design Artifacts Generated
✅ research.md - Technology decisions documented
✅ data-model.md - 22 dataclasses with validation rules
✅ api-contracts.yaml - OpenAPI 3.0.3 specification
✅ quickstart.md - Development guide with TDD workflow

### Architecture Review

| Principle | Status | Notes |
|-----------|--------|-------|
| **Service Layer Pattern** | ✅ PASS | 4 services created (log, cert, sql, http) per data-model.md |
| **Single Responsibility** | ✅ PASS | Each service handles one domain, models separate from logic |
| **Type Safety** | ✅ PASS | All models use dataclasses with type hints, mypy compliant |
| **API Design** | ✅ PASS | RESTful endpoints, OpenAPI documented, FastAPI integration |
| **Performance** | ✅ PASS | Async I/O, virtual scrolling, memory-efficient streaming |
| **Security** | ✅ PASS | Input validation, SQL injection prevention, credential masking |

### Technology Stack Validation

**New Dependencies Approved**:
- Python: httpx, aiosqlite, asyncpg, cryptography, python-dateutil, openpyxl, certifi
- JavaScript: CodeMirror 6, Chart.js, D3.js, Prism.js
- All choices documented in research.md with rationale

**Performance Targets Met**:
- Bundle sizes optimized (CodeMirror vs Monaco: 15x smaller)
- Virtual scrolling for 100k+ rows
- Async streaming for real-time logs
- Memory-efficient direct database access (no ORM overhead)

### Risk Assessment Post-Design

**No new risks identified**. Design maintains:
- Existing OSC sequence pattern (1337/1338)
- Existing FastAPI + HTMX architecture
- Existing SQLite storage approach
- Existing WebSocket infrastructure

### Final Gate: Ready for Implementation

✅ **APPROVED** - Feature 003-cat-commands ready for `/speckit.tasks` command

**Next Steps**:
1. Run `/speckit.tasks` to generate dependency-ordered implementation tasks
2. Follow TDD workflow from quickstart.md
3. Implement in priority order: logcat (P1) → certcat/sqlcat (P2) → curlcat (P3)
