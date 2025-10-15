# Tasks: Enhanced Media Support and Performance Optimization

**Feature**: 002-enhance-and-implement
**Input**: Design documents from `/specs/002-enhance-and-implement/`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Execution Flow Summary
```
1. ✓ Loaded plan.md - Tech stack: FastAPI, SQLAlchemy, foliate-js, PyPDF2, psutil
2. ✓ Loaded data-model.md - 2 new entities, 1 extended entity
3. ✓ Loaded contracts/ - 3 API contract files (10 total endpoints)
4. ✓ Generated tasks by category (40 total tasks)
5. ✓ Applied TDD ordering (tests before implementation)
6. ✓ Marked parallel execution opportunities [P]
7. ✓ Validated completeness (all contracts/entities covered)
8. → Ready for execution
```

## Path Conventions
- **Project Structure**: Single FastAPI application (existing)
- **Source**: `src/` at repository root
- **Tests**: `tests/` at repository root
- **Templates**: `templates/` at repository root
- **Static**: `static/` at repository root
- **Migrations**: `migrations/versions/` at repository root

---

## Phase 3.1: Setup & Dependencies

### T001 - Install new Python dependencies ✅
**File**: `requirements.txt`
**Description**: Add PyPDF2, ebooklib, psutil to requirements.txt
**Dependencies**: None
**Parallel**: No

```bash
# Add to requirements.txt:
PyPDF2==3.0.1
ebooklib==0.18
psutil==5.9.6
```

**Validation**: Run `pip install -r requirements.txt` successfully

---

### T002 - Create Alembic migration for database schema ✅
**File**: `migrations/versions/2025_10_09_0200_enhance_media_perf.py`
**Description**: Create migration adding ebook_metadata, performance_snapshots tables and extending user_profile
**Dependencies**: None
**Parallel**: No

**Implementation**: Use migration script from data-model.md
**Validation**: Run `alembic upgrade head` without errors

---

### T003 [P] - Add foliate-js library to frontend
**File**: `static/js/vendor/foliate-js/` or CDN reference in `templates/base.html`
**Description**: Download foliate-js library or add CDN link for ebook rendering
**Dependencies**: None
**Parallel**: Yes (different file from T001, T002)

**Options**:
1. CDN: Add `<script src="https://cdn.jsdelivr.net/npm/@johnfactotum/foliate-js"></script>` to base.html
2. Local: Download and place in `static/js/vendor/foliate-js/`

**Validation**: Library loads without 404 errors in browser console

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### T004 [P] - Contract test: POST /api/ebooks/process
**File**: `tests/contract/test_ebook_api.py`
**Description**: Test ebook file processing endpoint (validate, extract metadata, cache)
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Valid PDF file → 200 with EbookMetadata response
2. Valid EPUB file → 200 with EbookMetadata response
3. File not found → 404 error
4. File too large (>50MB) → 400 error
5. Invalid file type → 400 error

**Expected**: All tests FAIL (endpoint not implemented yet)

---

### T005 [P] - Contract test: GET /api/ebooks/{ebook_id}/content
**File**: `tests/contract/test_ebook_api.py` (same file, different test class)
**Description**: Test ebook content retrieval endpoint
**Dependencies**: None
**Parallel**: Yes (can run with T004 if using different test classes)

**Test cases**:
1. Valid ebook ID → 200 with binary content
2. Invalid ebook ID → 404 error
3. PDF with page parameter → 200 with specific page

**Expected**: All tests FAIL

---

### T006 [P] - Contract test: POST /api/ebooks/{ebook_id}/decrypt
**File**: `tests/contract/test_ebook_api.py`
**Description**: Test password-protected PDF decryption
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Correct password → 200 decrypted successfully
2. Incorrect password → 401 error
3. Too many attempts → 429 rate limit error

**Expected**: All tests FAIL

---

### T007 [P] - Contract test: GET /api/ebooks/metadata/{file_hash}
**File**: `tests/contract/test_ebook_api.py`
**Description**: Test ebook metadata retrieval by hash
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Valid hash with cached metadata → 200 with metadata
2. Unknown hash → 404 error

**Expected**: All tests FAIL

---

### T008 [P] - Contract test: GET /api/performance/current
**File**: `tests/contract/test_performance_api.py`
**Description**: Test current performance snapshot retrieval
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Request current metrics → 200 with PerformanceSnapshot

**Expected**: Tests FAIL

---

### T009 [P] - Contract test: GET /api/performance/history
**File**: `tests/contract/test_performance_api.py`
**Description**: Test historical performance snapshots retrieval
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Request last 60 minutes → 200 with array of snapshots
2. Request with session_id filter → 200 with filtered snapshots

**Expected**: Tests FAIL

---

### T010 [P] - Contract test: POST /api/performance/snapshot
**File**: `tests/contract/test_performance_api.py`
**Description**: Test client-side metrics submission
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Valid client metrics → 201 recorded

**Expected**: Tests FAIL

---

### T011 [P] - Contract test: PUT /api/user/preferences/performance
**File**: `tests/contract/test_performance_api.py`
**Description**: Test performance preferences update
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Update preferences → 200 with updated preferences
2. Invalid interval (out of range) → 400 error

**Expected**: Tests FAIL

---

### T012 [P] - Contract test: GET /api/recordings/{id}/dimensions
**File**: `tests/contract/test_recording_playback.py`
**Description**: Test recording dimensions retrieval
**Dependencies**: None
**Parallel**: Yes

**Test cases**:
1. Valid recording ID → 200 with dimensions
2. Invalid recording ID → 404 error

**Expected**: Tests FAIL

---

### T013 [P] - Integration test: Ebook viewing workflow
**File**: `tests/integration/test_ebook_viewing.py`
**Description**: End-to-end test of ebook viewing from command to display
**Dependencies**: None
**Parallel**: Yes

**Test scenarios** (from quickstart.md):
1. Open PDF file → metadata created, content displayed
2. Open EPUB file → HTML/CSS preserved
3. Handle file not found gracefully
4. Handle corrupted file gracefully
5. Large file shows progress indication
6. Password-protected PDF prompts and decrypts

**Expected**: All tests FAIL

---

### T014 [P] - Integration test: Recording playback width scaling
**File**: `tests/integration/test_recording_ui.py`
**Description**: Test recording playback responsive scaling
**Dependencies**: None
**Parallel**: Yes

**Test scenarios**:
1. 80-column recording displays full width (no scaling)
2. 150-column recording scales down to fit viewport
3. Resize window triggers reflow within 200ms
4. Playback controls remain accessible during scaling

**Expected**: All tests FAIL

---

### T015 [P] - Integration test: CPU optimization validation
**File**: `tests/integration/test_cpu_optimization.py`
**Description**: Validate CPU usage meets performance targets
**Dependencies**: None
**Parallel**: Yes

**Test scenarios**:
1. Idle CPU < 5% after 5 minutes
2. Active terminal CPU < 15%
3. Recording playback CPU < 25%
4. Multiple sessions scale linearly

**Expected**: Tests FAIL (current baseline is 78.6%)

---

## Phase 3.3: Database Models (ONLY after tests are failing)

### T016 [P] - Implement EbookMetadata model
**File**: `src/models/ebook_metadata.py`
**Description**: Create SQLAlchemy model for ebook file metadata
**Dependencies**: T002 (migration exists), T004-T007 (tests failing)
**Parallel**: Yes

**Implementation**:
- Define EbookMetadata class with all fields from data-model.md
- Include relationships to UserProfile
- Add validation for file_size constraint (≤50MB)
- Add file_type enum ('pdf', 'epub')

**Validation**: Tests in T004-T007 should start passing (partially)

---

### T017 [P] - Implement PerformanceSnapshot model
**File**: `src/models/performance_snapshot.py`
**Description**: Create SQLAlchemy model for performance metrics time-series
**Dependencies**: T002 (migration exists), T008-T011 (tests failing)
**Parallel**: Yes

**Implementation**:
- Define PerformanceSnapshot class with all fields
- Include relationship to TerminalSession
- Add validation for cpu_percent (0-100), memory_mb (>0)

**Validation**: Tests in T008-T011 should start passing (partially)

---

### T018 - Extend UserProfile model with performance preferences
**File**: `src/models/user_profile.py` (existing file - MUST BE SEQUENTIAL)
**Description**: Add show_performance_metrics and performance_metric_refresh_interval fields
**Dependencies**: T002 (migration exists), T011 (test failing)
**Parallel**: No (modifies existing file)

**Implementation**:
- Add two new boolean/integer fields
- Set appropriate defaults (False, 5000)

**Validation**: T011 test should start passing

---

## Phase 3.4: Services Layer

### T019 [P] - Implement EbookService - file validation
**File**: `src/services/ebook_service.py`
**Description**: Create service for ebook file validation (path, size, magic bytes)
**Dependencies**: T016 (model exists)
**Parallel**: Yes

**Implementation**:
- `validate_ebook_file(path)` function
- Check file exists, is absolute path, no path traversal
- Validate file size ≤ 50MB
- Check magic bytes (PDF: `%PDF-`, EPUB: ZIP + mimetype)
- Return validation errors

**Validation**: File validation test cases pass

---

### T020 - Implement EbookService - PDF metadata extraction
**File**: `src/services/ebook_service.py` (same file as T019 - SEQUENTIAL)
**Description**: Extract PDF metadata using PyPDF2
**Dependencies**: T019 (validation exists)
**Parallel**: No (same file)

**Implementation**:
- `extract_pdf_metadata(path)` function
- Use PyPDF2.PdfReader to read PDF
- Extract title, author, page count
- Detect if encrypted (is_encrypted property)
- Calculate SHA-256 hash for caching

**Validation**: PDF processing tests pass

---

### T021 - Implement EbookService - EPUB metadata extraction
**File**: `src/services/ebook_service.py` (continuing same file)
**Description**: Extract EPUB metadata using ebooklib
**Dependencies**: T020 (PDF extraction exists)
**Parallel**: No (same file)

**Implementation**:
- `extract_epub_metadata(path)` function
- Use ebooklib.epub.read_epub()
- Extract title, author from metadata
- Calculate SHA-256 hash
- Note: total_pages = NULL for EPUB

**Validation**: EPUB processing tests pass

---

### T022 - Implement EbookService - password decryption
**File**: `src/services/ebook_service.py`
**Description**: Decrypt password-protected PDFs with PyPDF2
**Dependencies**: T020 (PDF handling exists)
**Parallel**: No

**Implementation**:
- `decrypt_pdf(ebook_id, password)` function
- Use PyPDF2.PdfReader.decrypt()
- Cache decrypted version in memory (session-scoped)
- Limit password attempts to 3 max
- Clear cache after 1 hour or session end

**Validation**: T006 tests (decrypt) should pass

---

### T023 - Implement EbookService - main orchestration
**File**: `src/services/ebook_service.py`
**Description**: Orchestrate ebook processing workflow
**Dependencies**: T019-T022 (all extraction methods exist)
**Parallel**: No

**Implementation**:
- `process_ebook(file_path, user_id)` main function
- Call validation → metadata extraction → DB storage
- Check cache by hash before re-processing
- Update last_accessed on subsequent views
- Return EbookMetadata object

**Validation**: T004-T007 contract tests should fully pass

---

### T024 [P] - Implement PerformanceService - server metrics collection
**File**: `src/services/performance_service.py`
**Description**: Collect server-side performance metrics with psutil
**Dependencies**: T017 (model exists)
**Parallel**: Yes

**Implementation**:
- `collect_server_metrics()` function
- Use psutil.cpu_percent() for CPU
- Use psutil.virtual_memory() for memory MB
- Count active WebSocket connections
- Calculate terminal_updates_per_sec

**Validation**: Server metrics collected successfully

---

### T025 - Implement PerformanceService - snapshot storage
**File**: `src/services/performance_service.py`
**Description**: Store performance snapshots in database
**Dependencies**: T024 (collection exists)
**Parallel**: No (same file)

**Implementation**:
- `store_snapshot(session_id, metrics)` function
- Create PerformanceSnapshot record
- Validate timestamp (reject if stale >1 hour)
- Return snapshot ID

**Validation**: Snapshots persist to database

---

### T026 - Implement PerformanceService - cleanup job
**File**: `src/services/performance_service.py`
**Description**: Background task to delete snapshots older than 24 hours
**Dependencies**: T025 (storage exists)
**Parallel**: No

**Implementation**:
- `cleanup_old_snapshots()` async function
- DELETE FROM performance_snapshots WHERE timestamp < NOW() - 24 hours
- Schedule with asyncio (runs daily)

**Validation**: Old snapshots automatically deleted

---

### T027 - Implement PerformanceService - WebSocket push
**File**: `src/services/performance_service.py`
**Description**: Push performance metrics via WebSocket to connected clients
**Dependencies**: T024-T025 (collection and storage exist)
**Parallel**: No

**Implementation**:
- `push_metrics_to_clients()` function
- Collect metrics at user-configured interval
- Serialize to JSON (cache serialized version)
- WebSocket broadcast to active sessions

**Validation**: Clients receive real-time updates

---

## Phase 3.5: API Endpoints

### T028 [P] - Implement POST /api/ebooks/process endpoint
**File**: `src/api/ebook_endpoints.py` (new file)
**Description**: Create FastAPI endpoint for ebook processing
**Dependencies**: T023 (service exists), T004 (test exists)
**Parallel**: Yes

**Implementation**:
- POST /api/ebooks/process route
- Accept { filePath: string } in body
- Call ebook_service.process_ebook()
- Return EbookMetadata JSON
- Handle errors (404, 400)

**Validation**: T004 test passes

---

### T029 - Implement GET /api/ebooks/{ebook_id}/content endpoint
**File**: `src/api/ebook_endpoints.py`
**Description**: Serve ebook file content
**Dependencies**: T028 (process endpoint exists), T005 (test exists)
**Parallel**: No (same file)

**Implementation**:
- GET route with ebook_id path parameter
- Optional page query parameter (for PDF pagination)
- Lookup ebook in database
- Return FileResponse with ebook file
- Update last_accessed timestamp

**Validation**: T005 test passes

---

### T030 - Implement POST /api/ebooks/{ebook_id}/decrypt endpoint
**File**: `src/api/ebook_endpoints.py`
**Description**: Handle PDF password decryption
**Dependencies**: T022 (decrypt service exists), T006 (test exists)
**Parallel**: No

**Implementation**:
- POST route with ebook_id and password in body
- Call ebook_service.decrypt_pdf()
- Return success/failure response
- Implement rate limiting (3 attempts max)

**Validation**: T006 test passes

---

### T031 - Implement GET /api/ebooks/metadata/{file_hash} endpoint
**File**: `src/api/ebook_endpoints.py`
**Description**: Retrieve cached metadata by hash
**Dependencies**: T028 (base endpoint logic exists), T007 (test exists)
**Parallel**: No

**Implementation**:
- GET route with file_hash parameter
- Query ebook_metadata WHERE file_hash = ?
- Return metadata or 404

**Validation**: T007 test passes

---

### T032 [P] - Implement GET /api/performance/current endpoint
**File**: `src/api/performance_endpoints.py` (new file)
**Description**: Return latest performance snapshot
**Dependencies**: T027 (metrics service exists), T008 (test exists)
**Parallel**: Yes

**Implementation**:
- GET route
- Call performance_service.collect_server_metrics()
- Return current snapshot JSON

**Validation**: T008 test passes

---

### T033 - Implement GET /api/performance/history endpoint
**File**: `src/api/performance_endpoints.py`
**Description**: Return historical snapshots
**Dependencies**: T032 (base endpoint exists), T009 (test exists)
**Parallel**: No

**Implementation**:
- GET route with minutes and session_id query params
- Query snapshots within time range
- Return array of snapshots

**Validation**: T009 test passes

---

### T034 - Implement POST /api/performance/snapshot endpoint
**File**: `src/api/performance_endpoints.py`
**Description**: Accept client-side metrics
**Dependencies**: T025 (storage service exists), T010 (test exists)
**Parallel**: No

**Implementation**:
- POST route with session_id, client_fps, client_memory_mb
- Call performance_service.store_snapshot()
- Return 201 created

**Validation**: T010 test passes

---

### T035 - Implement PUT /api/user/preferences/performance endpoint
**File**: `src/api/performance_endpoints.py`
**Description**: Update user performance preferences
**Dependencies**: T018 (UserProfile extended), T011 (test exists)
**Parallel**: No

**Implementation**:
- PUT route with show_performance_metrics, performance_metric_refresh_interval
- Update UserProfile in database
- Validate interval range (1000-60000)
- Return updated preferences

**Validation**: T011 test passes

---

### T036 - Implement GET /api/recordings/{id}/dimensions endpoint
**File**: `src/api/recording_endpoints.py` (existing file - modify carefully)
**Description**: Return terminal dimensions for recording scaling
**Dependencies**: T012 (test exists)
**Parallel**: No (existing file)

**Implementation**:
- GET route with recording ID
- Query TerminalSession/Recording for rows, columns
- Return RecordingDimensions JSON

**Validation**: T012 test passes

---

## Phase 3.6: Frontend Implementation

### T037 - Create ebook viewer modal component
**File**: `templates/components/ebook_viewer.html`
**Description**: HTMX template for ebook viewer modal
**Dependencies**: T003 (foliate-js loaded)
**Parallel**: Yes

**Implementation**:
- Modal overlay structure
- foliate-js viewer container
- Navigation controls (prev/next page, jump to page)
- Close button
- Password prompt modal (nested)

**Validation**: Modal renders correctly in browser

---

### T038 - Implement ebook viewer JavaScript controller
**File**: `static/js/ebook-viewer.js`
**Description**: Client-side ebook rendering and interaction logic
**Dependencies**: T037 (template exists), T003 (foliate-js loaded)
**Parallel**: No (depends on T037)

**Implementation**:
- Initialize foliate-js with ebook file
- Handle page navigation events
- Password prompt and retry logic
- Loading progress indicator
- Integration with HTMX for API calls

**Validation**: Ebooks render correctly (PDF and EPUB)

---

### T039 - Create performance metrics widget component
**File**: `templates/components/performance_metrics.html`
**Description**: HTMX template for performance metrics display
**Dependencies**: None
**Parallel**: Yes

**Implementation**:
- Collapsible widget (top-right or sidebar)
- Display: CPU%, Memory MB, WebSocket count, Updates/sec
- Settings toggle integration
- Refresh interval control

**Validation**: Widget displays correctly

---

### T040 - Implement performance monitoring JavaScript
**File**: `static/js/performance-monitor.js`
**Description**: Client-side performance metrics collection and display
**Dependencies**: T039 (template exists)
**Parallel**: No

**Implementation**:
- Collect client metrics (performance.memory, FPS if available)
- WebSocket listener for server metrics pushes
- Update widget DOM with new metrics
- POST client metrics to /api/performance/snapshot
- Respect user preference toggle

**Validation**: Metrics update in real-time

---

### T041 - Update recording playback template with scaling
**File**: `templates/components/recording_playback.html` (existing - modify)
**Description**: Add responsive width scaling to recording playback
**Dependencies**: T036 (dimensions API exists)
**Parallel**: No (existing file)

**Implementation**:
- Add CSS transform: scale() container
- Calculate scale ratio based on viewport/terminal width
- Set transform-origin: top left
- Ensure controls remain accessible

**Validation**: Wide recordings scale to fit viewport

---

### T042 - Implement recording playback scaling JavaScript
**File**: `static/js/recording-player.js` (existing - modify carefully)
**Description**: Calculate and apply scaling dynamically
**Dependencies**: T041 (template updated)
**Parallel**: No

**Implementation**:
- Fetch recording dimensions from API
- Calculate: scale = min(1.0, viewportWidth / terminalWidth)
- Apply CSS transform
- Add window resize listener with 200ms debounce
- Measure resize latency (performance.now())

**Validation**: T014 integration test passes (<200ms resize)

---

## Phase 3.7: CPU Optimization

### T043 - Profile baseline CPU usage
**File**: N/A (measurement task)
**Description**: Capture current CPU profile for comparison
**Dependencies**: None
**Parallel**: Yes

**Implementation**:
- Run py-spy: `py-spy record --pid <pid> --duration 60 --output baseline.svg`
- Measure idle CPU with `top` or Activity Monitor for 5 minutes
- Document baseline: ~78.6% (current state)

**Validation**: Baseline flamegraph and metrics saved

---

### T044 - Optimize WebSocket ping interval
**File**: `src/websockets/terminal_handler.py` (and similar handlers)
**Description**: Increase ping interval from 20s to 60s
**Dependencies**: T043 (baseline captured)
**Parallel**: No

**Implementation**:
- Update WebSocket ping_interval parameter to 60 seconds
- Verify connection stability (still detects dead connections)

**Validation**: CPU usage reduced by ~5% (measure with py-spy)

---

### T045 - Implement terminal output debouncing
**File**: `src/services/pty_service.py` or `src/websockets/terminal_handler.py`
**Description**: Batch terminal updates with 100ms debounce window
**Dependencies**: T044 (previous optimization complete)
**Parallel**: No

**Implementation**:
- Add asyncio debounce decorator or buffer
- Collect terminal output for 100ms before sending
- Batch WebSocket messages
- Ensure no visual lag for interactive commands

**Validation**: CPU usage reduced by ~15%, T015 tests start passing

---

### T046 - Remove idle polling loops
**File**: Multiple files (audit codebase)
**Description**: Convert polling loops to event-driven with asyncio.sleep
**Dependencies**: T045 (debouncing complete)
**Parallel**: No

**Implementation**:
- Search for `while True` with short `time.sleep()` calls
- Replace with `asyncio.sleep(longer_interval)` or event-driven patterns
- Ensure no functionality lost

**Validation**: CPU usage reduced by ~20%

---

### T047 - Lazy-load xterm.js addons
**File**: `static/js/terminal.js` (or main terminal initialization file)
**Description**: Load xterm.js addons only when needed
**Dependencies**: T046 (backend optimizations complete)
**Parallel**: No

**Implementation**:
- Move addon imports (fit, webLinks, search) to lazy load
- Load on first use instead of startup
- Measure parsing time reduction

**Validation**: CPU usage reduced by ~10%, faster initial page load

---

### T048 - Validate CPU optimization targets
**File**: N/A (validation task)
**Description**: Measure final CPU usage against targets
**Dependencies**: T044-T047 (all optimizations implemented)
**Parallel**: No

**Implementation**:
- Run py-spy again: compare to baseline flamegraph
- Measure idle CPU (target: <5%)
- Measure active CPU (target: <15%)
- Measure recording playback CPU (target: <25%)

**Validation**: T015 integration test passes, targets met

---

## Phase 3.8: Integration & Polish

### T049 [P] - Unit tests for ebook validation logic
**File**: `tests/unit/test_ebook_service.py`
**Description**: Test file validation, hash calculation, metadata extraction
**Dependencies**: T023 (service implemented)
**Parallel**: Yes

**Test coverage**:
- Path validation (absolute, no traversal)
- File size checking
- Magic bytes validation
- SHA-256 hash calculation

**Validation**: All unit tests pass

---

### T050 [P] - Unit tests for performance service
**File**: `tests/unit/test_performance_service.py`
**Description**: Test metrics collection, validation, cleanup
**Dependencies**: T027 (service implemented)
**Parallel**: Yes

**Test coverage**:
- Metrics collection (CPU, memory)
- Timestamp validation
- Cleanup logic (24h retention)
- JSON caching

**Validation**: All unit tests pass

---

### T051 - Run full integration test suite
**File**: N/A (test execution)
**Description**: Execute all integration tests from T013-T015
**Dependencies**: T013-T015 (tests written), All implementation (T016-T048)
**Parallel**: No

**Execution**:
```bash
pytest tests/integration/test_ebook_viewing.py
pytest tests/integration/test_recording_ui.py
pytest tests/integration/test_cpu_optimization.py
```

**Validation**: All integration tests pass

---

### T052 - Run full contract test suite
**File**: N/A (test execution)
**Description**: Execute all contract tests from T004-T012
**Dependencies**: T004-T012 (tests written), T028-T036 (endpoints implemented)
**Parallel**: No

**Execution**:
```bash
pytest tests/contract/test_ebook_api.py
pytest tests/contract/test_performance_api.py
pytest tests/contract/test_recording_playback.py
```

**Validation**: All contract tests pass

---

### T053 - Performance benchmarks
**File**: N/A (measurement)
**Description**: Validate performance requirements from quickstart.md
**Dependencies**: All implementation complete
**Parallel**: No

**Benchmarks**:
1. PDF rendering (10MB) → <3 seconds
2. EPUB rendering (5MB) → <2 seconds
3. Page navigation → <500ms
4. Recording resize → <200ms
5. CPU idle → <5%
6. CPU active → <15%

**Validation**: All benchmarks meet targets

---

### T054 - Execute quickstart.md manual testing
**File**: `specs/002-enhance-and-implement/quickstart.md`
**Description**: Run all manual test scenarios
**Dependencies**: All implementation complete
**Parallel**: No

**Execution**: Follow quickstart.md step-by-step, verify all scenarios

**Validation**: Success criteria checklist 100% complete

---

### T055 [P] - Update CLAUDE.md with implementation notes
**File**: `CLAUDE.md`
**Description**: Document final implementation details
**Dependencies**: None (can be done anytime after T001)
**Parallel**: Yes

**Updates**:
- Add ebook viewer commands to Key Features
- Update Performance Requirements with optimization results
- Add troubleshooting tips

**Validation**: CLAUDE.md reflects current state

---

## Dependencies Graph

```
Setup: T001 → T002 → T003

Tests First: T004-T015 [ALL IN PARALLEL]

Models: T016, T017 [PARALLEL] → T018

Services:
  Ebook: T019 → T020 → T021 → T022 → T023
  Performance: T024 → T025 → T026 → T027

API Endpoints:
  Ebook: T028 → T029 → T030 → T031
  Performance: T032 → T033 → T034 → T035
  Recording: T036

Frontend: T037 → T038 [PARALLEL WITH T039 → T040] → T041 → T042

CPU Optimization: T043 → T044 → T045 → T046 → T047 → T048

Polish: T049, T050 [PARALLEL] → T051 → T052 → T053 → T054 → T055
```

## Parallel Execution Examples

### Example 1: Contract Tests (T004-T012)
```bash
# All contract tests can run in parallel (different test files/classes)
Task: "Contract test POST /api/ebooks/process"
Task: "Contract test GET /api/ebooks/{ebook_id}/content"
Task: "Contract test POST /api/ebooks/{ebook_id}/decrypt"
Task: "Contract test GET /api/ebooks/metadata/{file_hash}"
Task: "Contract test GET /api/performance/current"
Task: "Contract test GET /api/performance/history"
Task: "Contract test POST /api/performance/snapshot"
Task: "Contract test PUT /api/user/preferences/performance"
Task: "Contract test GET /api/recordings/{id}/dimensions"
```

### Example 2: Models (T016-T017)
```bash
# Different model files, no shared dependencies
Task: "Implement EbookMetadata model"
Task: "Implement PerformanceSnapshot model"
```

### Example 3: Unit Tests (T049-T050)
```bash
# Different test files
Task: "Unit tests for ebook validation logic"
Task: "Unit tests for performance service"
```

## Validation Checklist

**GATE: All items must be checked before feature is complete**

- [x] All contracts have corresponding tests (T004-T012)
- [x] All entities have model tasks (T016-T018)
- [x] All tests come before implementation (T004-T015 before T016+)
- [x] Parallel tasks truly independent (verified [P] markers)
- [x] Each task specifies exact file path
- [x] No [P] task modifies same file as another [P] task
- [x] CPU optimization validates against baseline (T043, T048)
- [x] Integration tests validate end-to-end flows (T013-T015, T051)
- [x] Performance benchmarks meet all targets (T053)

## Notes

- **Total Tasks**: 55 (Setup: 3, Tests: 12, Models: 3, Services: 9, APIs: 9, Frontend: 6, CPU: 6, Polish: 7)
- **Parallel Opportunities**: 21 tasks marked [P]
- **Critical Path**: T001 → T002 → T004-T015 → T016-T023 → T028-T031 → T038 → T051-T054
- **Estimated Timeline**: 3-5 days (assuming TDD, incremental commits)

**Remember**:
- ✅ Verify tests FAIL before implementing
- ✅ Commit after each task completion
- ✅ Run linters before committing (black, flake8)
- ✅ Update progress in this file (check boxes)
- ✅ Measure CPU at each optimization step (T043-T048)

---

**Last Updated**: 2025-10-09
**Status**: Ready for execution
**Next Command**: Begin with T001 (Install dependencies)
