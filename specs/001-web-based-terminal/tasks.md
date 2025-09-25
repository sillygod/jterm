# Tasks: Web-Based Terminal Emulator

**Input**: Design documents from `/specs/001-web-based-terminal/`
**Prerequisites**: plan.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✓ Extract: FastAPI, SQLite, HTMX, xterm.js, Hyperscript
2. Load optional design documents:
   → ✓ data-model.md: 7 entities → model tasks
   → ✓ contracts/: 5 files → contract test tasks
   → ✓ research.md: WebSocket architecture → setup tasks
3. Generate tasks by category:
   → Setup: FastAPI project init, SQLite, HTMX templates
   → Tests: contract tests, integration tests
   → Core: models, services, WebSocket handlers, HTMX endpoints
   → Integration: database, middleware, static assets
   → Polish: unit tests, performance, documentation
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. ✓ Generated dependency graph
7. ✓ Created parallel execution examples
8. ✓ Validated task completeness
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- All file paths are relative to repository root

## Path Conventions
- **Single project structure**: `src/`, `tests/`, `static/`, `templates/` at repository root
- Templates served directly by FastAPI with HTMX
- Static assets for JavaScript/CSS

## Phase 3.1: Setup
- [ ] T001 Create FastAPI project structure with src/, tests/, static/, templates/ directories
- [ ] T002 Initialize Python project with FastAPI, SQLite, WebSocket dependencies per requirements.txt
- [ ] T003 [P] Configure linting (black, flake8) and formatting tools
- [ ] T004 [P] Set up SQLite database schema and Alembic migrations in src/database/
- [ ] T005 [P] Create base HTMX template structure in templates/base.html
- [ ] T006 [P] Set up static assets directory with xterm.js, HTMX, and Hyperscript

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (API Endpoints)
- [ ] T007 [P] Contract test terminal session WebSocket in tests/contract/test_terminal_session_ws.py
- [ ] T008 [P] Contract test terminal session REST APIs in tests/contract/test_terminal_session_rest.py
- [ ] T009 [P] Contract test media asset upload/render in tests/contract/test_media_assets.py
- [ ] T010 [P] Contract test session recording APIs in tests/contract/test_session_recording.py
- [ ] T011 [P] Contract test AI assistant APIs in tests/contract/test_ai_assistant.py
- [ ] T012 [P] Contract test themes/extensions APIs in tests/contract/test_themes_extensions.py

### Integration Tests (User Stories)
- [ ] T013 [P] Integration test terminal session creation and PTY communication in tests/integration/test_terminal_flow.py
- [ ] T014 [P] Integration test image/video viewing in terminal in tests/integration/test_media_viewing.py
- [ ] T015 [P] Integration test markdown rendering with split-pane in tests/integration/test_markdown_rendering.py
- [ ] T016 [P] Integration test HTML preview with sandboxing in tests/integration/test_html_preview.py
- [ ] T017 [P] Integration test session recording and playback in tests/integration/test_session_replay.py
- [ ] T018 [P] Integration test AI assistant with voice input in tests/integration/test_ai_assistant.py
- [ ] T019 [P] Integration test theme import and extension loading in tests/integration/test_customization.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models
- [ ] T020 [P] Terminal Session model in src/models/terminal_session.py
- [ ] T021 [P] Recording model in src/models/recording.py
- [ ] T022 [P] Media Asset model in src/models/media_asset.py
- [ ] T023 [P] Theme Configuration model in src/models/theme_config.py
- [ ] T024 [P] Extension model in src/models/extension.py
- [ ] T025 [P] AI Context model in src/models/ai_context.py
- [ ] T026 [P] User Profile model in src/models/user_profile.py

### Core Services
- [ ] T027 [P] PTY service for terminal process management in src/services/pty_service.py
- [ ] T028 [P] Media processing service for images/videos in src/services/media_service.py
- [ ] T029 [P] Session recording service in src/services/recording_service.py
- [ ] T030 [P] AI assistant service with provider abstraction in src/services/ai_service.py
- [ ] T031 [P] Theme management service in src/services/theme_service.py
- [ ] T032 [P] Extension management service in src/services/extension_service.py

### WebSocket Handlers
- [ ] T033 Terminal session WebSocket handler for PTY communication in src/websockets/terminal_handler.py
- [ ] T034 AI assistant WebSocket handler for real-time chat in src/websockets/ai_handler.py
- [ ] T035 Session recording WebSocket proxy in src/websockets/recording_handler.py

### HTMX Templates and Endpoints
- [ ] T036 Main terminal interface HTMX template in templates/terminal.html
- [ ] T037 [P] Media viewer HTMX components in templates/components/media_viewer.html
- [ ] T038 [P] Markdown split-pane HTMX template in templates/components/markdown_viewer.html
- [ ] T039 [P] HTML preview iframe HTMX component in templates/components/html_preview.html
- [ ] T040 [P] Session recording controls HTMX template in templates/components/recording_controls.html
- [ ] T041 [P] AI assistant sidebar HTMX template in templates/components/ai_sidebar.html
- [ ] T042 [P] Theme selector HTMX component in templates/components/theme_selector.html

### FastAPI Endpoints
- [ ] T043 Terminal session management endpoints in src/api/terminal_endpoints.py
- [ ] T044 Media asset upload and serving endpoints in src/api/media_endpoints.py
- [ ] T045 Session recording CRUD endpoints in src/api/recording_endpoints.py
- [ ] T046 AI assistant REST endpoints in src/api/ai_endpoints.py
- [ ] T047 Theme and extension management endpoints in src/api/customization_endpoints.py

### Frontend JavaScript/Hyperscript
- [ ] T048 [P] xterm.js integration and terminal rendering in static/js/terminal.js
- [ ] T049 [P] Media rendering JavaScript for images/videos in static/js/media.js
- [ ] T050 [P] Session recording playback controls in static/js/recording.js
- [ ] T051 [P] Voice input integration with Web Speech API in static/js/voice.js
- [ ] T052 [P] Hyperscript behaviors for interactive elements in static/js/behaviors.hs

## Phase 3.4: Integration
- [ ] T053 Database connection and session management in src/database/connection.py
- [ ] T054 Authentication middleware for session security in src/middleware/auth.py
- [ ] T055 Request/response logging middleware in src/middleware/logging.py
- [ ] T056 Static file serving and CORS configuration in src/main.py
- [ ] T057 WebSocket connection management and cleanup in src/websockets/manager.py
- [ ] T058 File upload security validation and virus scanning in src/middleware/security.py

## Phase 3.5: Polish
- [ ] T059 [P] Unit tests for PTY service in tests/unit/test_pty_service.py
- [ ] T060 [P] Unit tests for media processing in tests/unit/test_media_service.py
- [ ] T061 [P] Unit tests for AI service in tests/unit/test_ai_service.py
- [ ] T062 [P] Unit tests for WebSocket handlers in tests/unit/test_websocket_handlers.py
- [ ] T063 Performance tests for <1s image loading in tests/performance/test_media_performance.py
- [ ] T064 Performance tests for <5% recording impact in tests/performance/test_recording_performance.py
- [ ] T065 [P] End-to-end browser tests with Playwright in tests/e2e/test_full_workflow.py
- [ ] T066 [P] Security audit for HTML sandboxing in tests/security/test_html_security.py
- [ ] T067 [P] API documentation generation in docs/api.md
- [ ] T068 [P] User guide documentation in docs/user_guide.md
- [ ] T069 Remove code duplication and optimize imports
- [ ] T070 Execute quickstart.md manual testing scenarios

## Dependencies
- **Setup (T001-T006)** before everything
- **Tests (T007-T019)** before implementation (T020-T058)
- **Models (T020-T026)** before services (T027-T032)
- **Services (T027-T032)** before WebSocket handlers (T033-T035)
- **Templates (T036-T042)** can run parallel with services
- **Endpoints (T043-T047)** after services and templates
- **Frontend JS (T048-T052)** after templates
- **Integration (T053-T058)** after core implementation
- **Polish (T059-T070)** after everything else

## Parallel Execution Examples

### Phase 3.2: Launch all contract tests together
```bash
# These can run simultaneously (different files, no dependencies):
Task: "Contract test terminal session WebSocket in tests/contract/test_terminal_session_ws.py"
Task: "Contract test terminal session REST APIs in tests/contract/test_terminal_session_rest.py"
Task: "Contract test media asset upload/render in tests/contract/test_media_assets.py"
Task: "Contract test session recording APIs in tests/contract/test_session_recording.py"
Task: "Contract test AI assistant APIs in tests/contract/test_ai_assistant.py"
Task: "Contract test themes/extensions APIs in tests/contract/test_themes_extensions.py"
```

### Phase 3.2: Launch all integration tests together
```bash
# These can run simultaneously (different files, testing different flows):
Task: "Integration test terminal session creation and PTY communication in tests/integration/test_terminal_flow.py"
Task: "Integration test image/video viewing in terminal in tests/integration/test_media_viewing.py"
Task: "Integration test markdown rendering with split-pane in tests/integration/test_markdown_rendering.py"
Task: "Integration test HTML preview with sandboxing in tests/integration/test_html_preview.py"
Task: "Integration test session recording and playback in tests/integration/test_session_replay.py"
Task: "Integration test AI assistant with voice input in tests/integration/test_ai_assistant.py"
Task: "Integration test theme import and extension loading in tests/integration/test_customization.py"
```

### Phase 3.3: Launch all data models together
```bash
# These can run simultaneously (different files, no dependencies):
Task: "Terminal Session model in src/models/terminal_session.py"
Task: "Recording model in src/models/recording.py"
Task: "Media Asset model in src/models/media_asset.py"
Task: "Theme Configuration model in src/models/theme_config.py"
Task: "Extension model in src/models/extension.py"
Task: "AI Context model in src/models/ai_context.py"
Task: "User Profile model in src/models/user_profile.py"
```

### Phase 3.3: Launch all core services together (after models)
```bash
# These can run simultaneously (different files, models already complete):
Task: "PTY service for terminal process management in src/services/pty_service.py"
Task: "Media processing service for images/videos in src/services/media_service.py"
Task: "Session recording service in src/services/recording_service.py"
Task: "AI assistant service with provider abstraction in src/services/ai_service.py"
Task: "Theme management service in src/services/theme_service.py"
Task: "Extension management service in src/services/extension_service.py"
```

## Notes
- **[P] tasks** = different files, no dependencies, can run in parallel
- **Verify tests fail** before implementing (TDD requirement)
- **Commit after each task** for clean history
- **SQLite database** auto-created on first run, no external dependencies
- **HTMX templates** served directly by FastAPI, no separate frontend build
- **WebSocket connections** handle real-time PTY and AI communication
- **File paths** are relative to repository root

## Task Generation Rules Applied

1. **From Contracts**: 5 contract files → 6 contract test tasks [P]
2. **From Data Model**: 7 entities → 7 model creation tasks [P]
3. **From User Stories**: 7 main stories → 7 integration test tasks [P]
4. **From Architecture**: WebSocket + HTMX → specialized handlers and templates
5. **Ordering**: Setup → Tests → Models → Services → Endpoints → Polish

## Validation Checklist ✓

- [x] All contracts have corresponding tests (T007-T012)
- [x] All entities have model tasks (T020-T026)
- [x] All tests come before implementation (T007-T019 before T020+)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] WebSocket and HTMX architecture properly covered
- [x] Performance requirements addressed (T063-T064)
- [x] Security requirements covered (T058, T066)