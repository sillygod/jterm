# Implementation Plan: Enhanced Media Support and Performance Optimization

**Branch**: `002-enhance-and-implement` | **Date**: 2025-10-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-enhance-and-implement/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   ✅ Loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   ✅ Project Type detected: Web application
   ✅ Structure Decision: Single project (existing FastAPI app)
3. Fill the Constitution Check section
   ✅ Constitution is template-only, applying sensible defaults
4. Evaluate Constitution Check section
   ✅ No violations - straightforward feature additions
   ✅ Progress Tracking: Initial Constitution Check PASS
5. Execute Phase 0 → research.md
   ✅ Research completed
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md update
   ✅ Design artifacts generated
7. Re-evaluate Constitution Check
   ✅ No new violations
   ✅ Progress Tracking: Post-Design Constitution Check PASS
8. Plan Phase 2 → Describe task generation approach
   ✅ Task strategy documented
9. STOP - Ready for /tasks command
   ✅ COMPLETE
```

## Summary

This feature adds three key enhancements to the jterm web terminal:

1. **Ebook Viewer (`bookcat` command)**: Display PDF and EPUB files directly in the browser using foliate-js library for rendering. Supports up to 50MB files, password-protected PDFs, navigation controls, and loading progress.

2. **Recording Playback UI Improvements**: Fix narrow terminal display in recording playback by implementing responsive width scaling (80-200 columns), with automatic content scaling when width exceeds viewport.

3. **CPU Usage Optimization**: Reduce idle CPU from 78.6% to <5% by optimizing WebSocket polling intervals, implementing terminal output buffering/throttling, and adding optional performance metrics display with user-configurable toggle.

**Technical Approach**:
- Frontend: foliate-js for ebook rendering, CSS transforms for recording scaling, JavaScript performance monitoring
- Backend: New FastAPI endpoints for ebook processing, performance snapshot collection, WebSocket optimization
- Storage: SQLite tables for ebook metadata and performance snapshots
- Testing: TDD approach with contract tests, integration tests, performance benchmarks

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES2022 (frontend)
**Primary Dependencies**:
- Backend: FastAPI 0.104+, SQLAlchemy 2.0+, PyPDF2 (PDF), ebooklib (EPUB), psutil (performance metrics)
- Frontend: xterm.js (existing), foliate-js (new for ebook rendering), HTMX 1.9+
**Storage**: SQLite (aiosqlite) + file system for media caching
**Testing**: pytest (backend), Jest (frontend), Playwright (E2E)
**Target Platform**: Modern web browsers (Chrome, Firefox, Safari latest versions)
**Project Type**: Web application (single FastAPI app with HTMX templates)
**Performance Goals**:
- PDF rendering: <3s for 10MB files
- EPUB rendering: <2s for 5MB files
- Page navigation: <500ms response
- CPU reduction: 78.6% → <5% idle, <15% active
- Recording playback resize: <200ms
**Constraints**:
- File size limit: 50MB maximum for ebooks
- Browser memory: Efficient memory management for large files
- Backward compatibility: Must not break existing terminal/recording features
**Scale/Scope**:
- Single-user focused (default user), multi-user ready
- Ebook library: hundreds of files per user
- Performance snapshots: 24-hour retention, time-series data
- Recording playback: up to 200 column wide terminals

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Constitution file is template-only. Applying sensible defaults based on project patterns.

✅ **Test-First Development**: All new features will have tests written before implementation
✅ **Service Layer Pattern**: New features use existing src/services/ architecture
✅ **Single Responsibility**: Each service handles one concern (ebook, performance, recording UI)
✅ **Type Hints**: All Python code includes type annotations
✅ **Error Handling**: Graceful degradation for file errors, performance monitoring failures
✅ **Security**: File validation, path traversal prevention, password handling
✅ **Performance**: Non-blocking async operations, efficient database queries

**No violations detected** - Feature aligns with existing project architecture.

## Project Structure

### Documentation (this feature)
```
specs/002-enhance-and-implement/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (generated)
├── data-model.md        # Phase 1 output (generated)
├── quickstart.md        # Phase 1 output (generated)
├── contracts/           # Phase 1 output (generated)
│   ├── ebook_api.yaml
│   ├── performance_api.yaml
│   └── recording_playback.yaml
└── tasks.md             # Phase 2 output (/tasks command - NOT created yet)
```

### Source Code (repository root)
```
src/
├── models/
│   ├── ebook_metadata.py        # NEW - Ebook file metadata
│   ├── performance_snapshot.py  # NEW - Performance metrics
│   └── user_profile.py          # MODIFIED - Add preferences
├── services/
│   ├── ebook_service.py         # NEW - PDF/EPUB processing
│   └── performance_service.py   # NEW - Metrics collection
├── api/
│   ├── ebook_endpoints.py       # NEW - Ebook API routes
│   └── performance_endpoints.py # NEW - Metrics API routes
└── websockets/
    └── terminal_handler.py      # MODIFIED - CPU optimization

templates/components/
├── ebook_viewer.html            # NEW - Ebook viewer modal
├── performance_metrics.html     # NEW - Metrics display widget
└── recording_playback.html      # MODIFIED - Add responsive scaling

static/
├── js/
│   ├── ebook-viewer.js          # NEW - Ebook UI controller
│   ├── performance-monitor.js   # NEW - Client-side metrics
│   └── recording-player.js      # MODIFIED - Scaling logic
└── css/
    ├── ebook-viewer.css         # NEW - Ebook styles
    └── performance-metrics.css  # NEW - Metrics styles

tests/
├── contract/
│   ├── test_ebook_api.py        # NEW - Ebook API contract tests
│   └── test_performance_api.py  # NEW - Performance API tests
├── integration/
│   ├── test_ebook_viewing.py    # NEW - End-to-end ebook tests
│   ├── test_recording_ui.py     # NEW - Recording playback tests
│   └── test_cpu_optimization.py # NEW - Performance validation
└── unit/
    ├── test_ebook_service.py    # NEW - Ebook processing logic
    └── test_performance_service.py # NEW - Metrics collection

migrations/versions/
└── 2025_10_09_enhance_media_perf.py # NEW - Database migration
```

**Structure Decision**: Single project (existing FastAPI architecture) - no need for separate backend/frontend

## Phase 0: Outline & Research

**Research Questions Investigated**:

1. **Ebook Rendering Library Selection**
   - **Decision**: Use foliate-js for both PDF and EPUB
   - **Rationale**: Pure JavaScript, no dependencies, supports both formats, modular design
   - **Alternatives Considered**:
     - PDF.js + epub.js (two separate libraries, more complexity)
     - Mozilla PDF.js only (no EPUB support)
     - Server-side rendering (higher CPU cost, defeats optimization goal)
   - **Implementation Notes**:
     - Foliate-js handles pagination, navigation, text selection
     - CSS multi-column for responsive layouts
     - Custom web components for different book layouts
     - Experimental PDF support acceptable for our use case

2. **Password-Protected PDF Handling**
   - **Decision**: Use PyPDF2 with password decryption backend-side before sending to client
   - **Rationale**: Security (passwords not stored), compatibility, performance
   - **Alternatives Considered**:
     - Client-side decryption (exposes password handling)
     - Storing encrypted files (unnecessary complexity)
   - **Implementation Notes**:
     - Prompt user for password via modal
     - Backend decrypts and caches decrypted version temporarily
     - Clear cache after session or timeout

3. **Performance Monitoring Approach**
   - **Decision**: Server-side psutil for Python process metrics + client-side performance.memory for browser
   - **Rationale**: Accurate system-level CPU/memory, lightweight, cross-platform
   - **Alternatives Considered**:
     - OS-specific tools (htop, Activity Monitor - not portable)
     - Third-party APM (DataDog, New Relic - overkill, cost)
     - Browser-only monitoring (incomplete picture)
   - **Implementation Notes**:
     - Sample at user-configured interval (default 5s)
     - Store in SQLite with 24-hour retention
     - WebSocket push for real-time updates

4. **CPU Optimization Strategies**
   - **Decision**: Multi-pronged approach targeting WebSocket polling, terminal buffering, idle loops
   - **Rationale**: Current 78.6% baseline suggests multiple inefficiencies
   - **Key Optimizations**:
     - Increase WebSocket ping interval from 20s → 60s (reduce wakeups)
     - Implement 100ms debounce for terminal output (batch updates)
     - Use asyncio.sleep() instead of polling loops
     - Lazy-load xterm.js addons (reduce initial parsing)
   - **Alternatives Considered**:
     - Process pooling (premature, single-user focused)
     - Different web framework (unnecessary migration)
   - **Testing Strategy**: Before/after CPU profiling with py-spy

5. **Recording Playback Scaling**
   - **Decision**: CSS transform: scale() with calculated ratio based on viewport/terminal width
   - **Rationale**: Hardware-accelerated, smooth, maintains text sharpness better than canvas
   - **Alternatives Considered**:
     - Canvas rendering (more blur, higher CPU)
     - Horizontal scroll (rejected per spec)
     - Font size reduction (breaks alignment)
   - **Implementation Notes**:
     - Calculate: scale = min(1.0, viewportWidth / terminalWidth)
     - Apply transform-origin: top left
     - Update on window resize with 200ms debounce

**Output**: See [research.md](./research.md) for detailed findings

## Phase 1: Design & Contracts

### Data Model

**New Entities** (see [data-model.md](./data-model.md)):

1. **EbookMetadata**: Stores file metadata, cache keys, encryption status
   - Fields: id, file_path, file_hash (SHA-256), file_type, file_size, title, author, total_pages, is_encrypted, created_at, last_accessed, user_id
   - Indexes: file_path, file_hash (unique), user_id
   - Constraints: file_size ≤ 52428800 (50MB)

2. **PerformanceSnapshot**: Time-series performance metrics
   - Fields: id, session_id, timestamp, cpu_percent, memory_mb, active_websockets, terminal_updates_per_sec, client_fps, client_memory_mb
   - Indexes: (session_id, timestamp), timestamp
   - Constraints: cpu_percent 0-100, memory_mb > 0
   - Retention: 24 hours auto-delete

**Modified Entities**:

3. **UserProfile** (extend existing):
   - Add: show_performance_metrics (bool, default false)
   - Add: performance_metric_refresh_interval (int, 1000-60000ms, default 5000)

### API Contracts

**Generated OpenAPI Specs** (see [contracts/](./contracts/)):

1. **Ebook API** ([contracts/ebook_api.yaml](./contracts/ebook_api.yaml)):
   - `POST /api/ebooks/process` - Process ebook file (validate, extract metadata, cache)
   - `GET /api/ebooks/{ebook_id}/content` - Retrieve ebook content (paginated)
   - `POST /api/ebooks/{ebook_id}/decrypt` - Decrypt password-protected PDF
   - `GET /api/ebooks/metadata/{file_hash}` - Get cached metadata by hash

2. **Performance API** ([contracts/performance_api.yaml](./contracts/performance_api.yaml)):
   - `GET /api/performance/current` - Get current performance snapshot
   - `GET /api/performance/history` - Get historical snapshots (time range)
   - `POST /api/performance/snapshot` - Submit client-side metrics
   - `PUT /api/user/preferences/performance` - Update performance display preferences

3. **Recording Playback** ([contracts/recording_playback.yaml](./contracts/recording_playback.yaml)):
   - `GET /api/recordings/{id}/dimensions` - Get terminal dimensions for scaling calculation
   - (Existing WebSocket endpoint modified for dimension negotiation)

### Contract Tests

**Failing tests generated** (as required by TDD):

- `tests/contract/test_ebook_api.py` - 8 tests (all failing initially)
- `tests/contract/test_performance_api.py` - 6 tests (all failing initially)
- `tests/contract/test_recording_playback.py` - 3 tests (modified existing, failing)

### Integration Test Scenarios

From user stories in spec.md:

1. **Ebook Viewing** ([tests/integration/test_ebook_viewing.py]()):
   - Test: Open PDF, verify render, navigate pages
   - Test: Open EPUB, verify HTML/CSS preservation
   - Test: Handle file not found error
   - Test: Handle corrupted file gracefully
   - Test: Large file with progress indication
   - Test: Password-protected PDF flow

2. **Recording Playback** ([tests/integration/test_recording_ui.py]()):
   - Test: 80-column recording displays full width
   - Test: 150-column recording scales down to fit
   - Test: Resize window triggers reflow within 200ms
   - Test: Playback controls remain accessible

3. **CPU Optimization** ([tests/integration/test_cpu_optimization.py]()):
   - Test: Idle CPU < 5% after 5 minutes
   - Test: Active terminal CPU < 15%
   - Test: Recording playback CPU < 25%
   - Test: Multiple sessions scale linearly

### Agent File Update

**Incremental CLAUDE.md Update**:
```bash
# Running update script (preserves manual additions)
.specify/scripts/bash/update-agent-context.sh claude
```

**New sections added**:
- Active Technologies: Add PyPDF2, ebooklib, psutil, foliate-js
- Key Features: Update media support to include PDF/EPUB
- Recent Changes: Add 002-enhance-and-implement entry
- Performance Requirements: Add ebook rendering targets, CPU optimization goals

**Output**: Updated CLAUDE.md at repository root

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

The `/tasks` command will load `.specify/templates/tasks-template.md` and generate approximately **35-40 tasks** organized as follows:

1. **Phase 0: Database & Models** (Tasks 1-5) [P=Parallel]:
   - [P] Create Alembic migration for new tables
   - [P] Implement EbookMetadata model
   - [P] Implement PerformanceSnapshot model
   - [P] Extend UserProfile model with preferences
   - Run migration and verify schema

2. **Phase 1: Ebook Service** (Tasks 6-15):
   - [P] Write contract tests for ebook API endpoints
   - [P] Implement PDF metadata extraction (PyPDF2)
   - [P] Implement EPUB metadata extraction (ebooklib)
   - [P] Implement file validation and size checking
   - Implement password decryption for PDFs
   - Implement SHA-256 caching logic
   - Implement ebook service (orchestration)
   - [P] Create ebook API endpoints
   - Frontend: Integrate foliate-js library
   - Frontend: Create ebook viewer modal component

3. **Phase 2: Performance Monitoring** (Tasks 16-25):
   - [P] Write contract tests for performance API
   - [P] Implement server-side metrics collection (psutil)
   - [P] Implement client-side metrics collection (performance.memory)
   - Implement performance snapshot storage
   - Implement snapshot cleanup job (24h retention)
   - [P] Create performance API endpoints
   - Frontend: Create performance metrics widget
   - Frontend: Implement user preference toggle
   - Implement WebSocket metrics push
   - Integration test: Verify metrics accuracy

4. **Phase 3: CPU Optimization** (Tasks 26-30):
   - Profile current CPU usage (baseline)
   - Optimize WebSocket ping interval (20s → 60s)
   - Implement terminal output debouncing (100ms)
   - Remove idle polling loops (use asyncio.sleep)
   - Lazy-load xterm.js addons

5. **Phase 4: Recording Playback UI** (Tasks 31-35):
   - [P] Write tests for recording dimension API
   - Calculate viewport/terminal width ratio
   - Implement CSS transform scaling
   - Add window resize listener with debounce
   - Update recording playback template
   - Integration test: Verify <200ms resize

6. **Phase 5: Integration & Validation** (Tasks 36-40):
   - Run all contract tests (expect pass)
   - Run integration test suite
   - CPU optimization validation (<5% idle)
   - Performance benchmark (PDF/EPUB render times)
   - Update quickstart.md with examples

**Ordering Strategy**:
- **TDD Order**: Contract tests before implementation
- **Dependency Order**: Database → Services → API → Frontend
- **Parallel Markers [P]**: Independent tasks can run concurrently
- **Integration Last**: Full system tests after all components

**Estimated Output**: 55 numbered tasks in tasks.md with clear dependencies and test-first approach (expanded from initial 35-40 estimate due to comprehensive test coverage)

**IMPORTANT**: This phase is executed by the `/tasks` command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following TDD principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

**No violations** - This section intentionally left empty.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (via /clarify)
- [x] Complexity deviations documented (N/A - no deviations)

---

**Ready for `/tasks` command** - All planning artifacts generated successfully.

*Based on project patterns - See `CLAUDE.md` and `specs/001-web-based-terminal/plan.md` for context*
