# Tasks: Desktop Application Conversion

**Input**: Design documents from `/specs/005-desktop-application/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tauri-commands.md

**Tests**: Tests are not explicitly requested in the specification, so test tasks are not included. The existing test suite from the web version will be reused.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a hybrid desktop application:
- **Existing**: `src/` (Python backend - REUSED), `static/` (frontend - REUSED), `templates/` (HTML - REUSED)
- **New**: `src-tauri/` (Rust Tauri code), `src-tauri/ui/` (desktop UI adaptations), `scripts/` (build scripts)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize Tauri project and configure build environment

- [X] T001 Install Rust toolchain (1.85+) and Cargo per quickstart.md prerequisites
- [X] T002 Install Tauri CLI via `cargo install tauri-cli`
- [X] T003 [P] Install PyInstaller 6.0+ via `pip install pyinstaller==6.0`
- [X] T004 Initialize Tauri project structure via `cargo tauri init` in repository root
- [X] T005 [P] Create `src-tauri/icons/` directory with application icons for macOS/Windows/Linux
- [X] T006 Configure `src-tauri/tauri.conf.json` with application metadata (name, version, bundle settings per plan.md)
- [X] T007 [P] Update `package.json` to add Tauri dependencies (@tauri-apps/api, @tauri-apps/cli)
- [X] T008 Create `scripts/build-python.sh` for PyInstaller bundling with platform detection
- [X] T009 [P] Create `scripts/build-tauri.sh` for complete desktop build workflow
- [X] T010 [P] Update `.gitignore` to exclude `src-tauri/target/`, `src-tauri/binaries/`, `dist/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core desktop infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T011 Implement Tauri main entry point in `src-tauri/src/main.rs` with app initialization and window creation
- [X] T012 Create Python backend launcher in `src-tauri/src/python/launcher.rs` to start PyInstaller-bundled backend as subprocess
- [X] T013 Implement backend health check in `src-tauri/src/python/health.rs` to verify Python server is ready
- [X] T014 [P] Create platform-specific database path resolver in `src-tauri/src/utils/db_path.rs` (macOS: ~/Library/Application Support, Windows: %APPDATA%, Linux: ~/.local/share)
- [X] T015 [P] Implement logging utility in `src-tauri/src/utils/logging.rs` for desktop-specific logs
- [X] T016 Modify `src/config.py` to detect desktop mode and use platform-specific database paths from environment variable
- [X] T017 Update `src/main.py` FastAPI startup to accept port as command-line argument for dynamic port allocation
- [X] T018 Create desktop entry HTML in `src-tauri/ui/index.html` that connects to Python backend at localhost
- [X] T019 [P] Create desktop-specific JavaScript in `src-tauri/ui/desktop.js` for Tauri API initialization
- [X] T020 [P] Create desktop-specific CSS in `src-tauri/ui/desktop.css` for native window styling
- [X] T021 Update `src-tauri/Cargo.toml` with required dependencies (tauri, serde, tokio, reqwest)
- [X] T022 Configure `src-tauri/tauri.conf.json` allowlist for clipboard, dialog, shell, fs, path, window permissions
- [X] T023 Test foundational setup: Launch Tauri dev mode (`cargo tauri dev`) and verify Python backend starts and UI loads

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Standalone Desktop Launch (Priority: P1) 🎯 MVP

**Goal**: Users can launch jterm as a native desktop application without requiring a web browser or manual server startup

**Independent Test**: Double-click the application icon and verify the terminal appears within 3 seconds without browser/server processes

### Implementation for User Story 1

- [X] T024 [US1] Implement PyInstaller spec file creation in `scripts/build-python.sh` with --onefile, hidden imports for uvicorn, FastAPI
- [X] T025 [US1] Add template/static file bundling to PyInstaller spec in `scripts/build-python.sh` using --add-data flags
- [X] T026 [US1] Implement Python executable launch logic in `src-tauri/src/python/launcher.rs` with subprocess management
- [X] T027 [US1] Implement dynamic port allocation in `src-tauri/src/python/launcher.rs` to find available port (8000-9000 range)
- [X] T028 [US1] Implement backend readiness polling in `src-tauri/src/python/health.rs` with /health endpoint checks (max 30s timeout)
- [X] T029 [US1] Configure WebView URL in `src-tauri/src/main.rs` to point to localhost:<dynamic_port>
- [X] T030 [US1] Implement graceful shutdown in `src-tauri/src/python/launcher.rs` to terminate Python process on app close
- [X] T031 [US1] Add database initialization check in `src/main.py` to create platform-specific database directory if not exists
- [X] T032 [US1] Implement default user profile creation in `src/main.py` lifespan manager for first launch
- [X] T033 [US1] Add app_ready Tauri command in `src-tauri/src/commands/system.rs` returning app version, platform, database path
- [X] T034 [US1] Add quit_app Tauri command in `src-tauri/src/commands/system.rs` with force parameter and cleanup logic
- [X] T035 [US1] Update `src-tauri/ui/desktop.js` to call app_ready on load and display app info
- [X] T036 [US1] Build desktop application using `scripts/build-python.sh` followed by `cargo tauri build`
- [X] T037 [US1] Test standalone launch on macOS/Windows/Linux: verify <3s launch, no browser, clean shutdown

**Checkpoint**: At this point, User Story 1 should be fully functional - application launches and shows terminal UI

---

## Phase 4: User Story 2 - Native Terminal Emulation (Priority: P1)

**Goal**: Users can interact with a fully functional terminal emulator that supports all shell operations

**Independent Test**: Execute shell commands (cd, ls, git, vim) and verify PTY interaction, output rendering, resize behavior

### Implementation for User Story 2

- [X] T038 [US2] Verify Python PTY service (`src/services/pty_service.py`) is bundled correctly by PyInstaller (already complete - just verify)
- [X] T039 [US2] Verify WebSocket terminal handler (`src/websockets/terminal_handler.py`) is bundled correctly (already complete - just verify)
- [X] T040 [US2] Test WebSocket connection from Tauri WebView to Python backend via ws://localhost:<port>/ws/terminal
- [X] T041 [US2] Verify xterm.js loads correctly in Tauri WebView from `static/js/terminal.js`
- [X] T042 [US2] Test terminal input: type commands in xterm.js and verify WebSocket sends to Python PTY service
- [X] T043 [US2] Test terminal output: verify Python PTY output is received via WebSocket and rendered in xterm.js
- [X] T044 [US2] Test terminal resize: resize Tauri window and verify terminal dimensions update via WebSocket
- [X] T045 [US2] Test shell shortcuts: verify Ctrl+C, Ctrl+Z, Ctrl+D are passed to shell, not intercepted by Tauri
- [X] T046 [US2] Test interactive programs: run vim, nano, htop and verify proper rendering and key handling
- [X] T047 [US2] Verify performance: check CPU usage <15% during active terminal use

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - terminal emulation fully functional

---

## Phase 5: User Story 3 - Native Menu Bar and Window Controls (Priority: P1)

**Goal**: Users can access application features through native OS menu bars and window controls

**Independent Test**: Click through menu items and keyboard shortcuts to verify they trigger web version's functionality

### Implementation for User Story 3

- [X] T048 [P] [US3] Create menu module in `src-tauri/src/commands/menu.rs` with platform detection (macOS vs Windows/Linux)
- [X] T049 [US3] Implement macOS application menu in `src-tauri/src/main.rs` (About, Preferences, Quit with Cmd shortcuts)
- [X] T050 [US3] Implement cross-platform File menu in `src-tauri/src/main.rs` (New Tab: Cmd+N/Ctrl+N, Close Tab: Cmd+W/Ctrl+W)
- [X] T051 [US3] Implement Edit menu in `src-tauri/src/main.rs` (Copy: Cmd+C/Ctrl+C, Paste: Cmd+V/Ctrl+V)
- [X] T052 [US3] Implement View menu in `src-tauri/src/main.rs` (Recording Controls, Performance Monitor, AI Assistant toggles)
- [X] T053 [US3] Implement Help menu with About dialog (Windows/Linux only, macOS uses app menu)
- [X] T054 [US3] Add update_menu_item Tauri command in `src-tauri/src/commands/menu.rs` to enable/disable/check menu items
- [X] T055 [US3] Add show_context_menu Tauri command in `src-tauri/src/commands/menu.rs` for right-click context menus
- [X] T056 [US3] Connect Copy menu item to terminal selection: call existing xterm.js copySelection() function
- [X] T057 [US3] Connect Paste menu item to terminal: call existing xterm.js paste() function
- [X] T058 [US3] Connect New Tab menu item to create terminal session via Python backend API
- [X] T059 [US3] Connect Close Tab menu item to terminate session via Python backend API
- [X] T060 [US3] Test menu bars on macOS: verify application menu, Cmd shortcuts work
- [X] T061 [US3] Test menu bars on Windows/Linux: verify File/Edit/View/Help menus, Ctrl shortcuts work
- [X] T062 [US3] Test context menus: right-click in terminal and verify Copy/Paste/Clear options

**Checkpoint**: All P1 user stories (1, 2, 3) should now be complete - MVP is ready for delivery

---

## Phase 6: User Story 4 - Inline Media Viewing (Priority: P2)

**Goal**: Users can view images, videos, PDFs, EPUBs inline using cat commands

**Independent Test**: Run `imgcat image.png`, `bookcat document.pdf` and verify media renders inline

### Implementation for User Story 4

- [X] T063 [US4] Verify media service (`src/services/media_service.py`) is bundled correctly by PyInstaller (already complete)
- [X] T064 [US4] Verify ebook service (`src/services/ebook_service.py`) is bundled correctly by PyInstaller (already complete)
- [X] T065 [US4] Verify media API endpoints (`src/api/media.py`) are accessible from Tauri WebView
- [x] T066 [US4] Test image rendering: run `imgcat test.png` and verify image displays in <1 second
- [x] T067 [US4] Test video playback: run video cat command and verify HTML5 video controls work (play, pause, seek)
- [x] T068 [US4] Test PDF rendering: run `bookcat document.pdf` and verify foliate-js loads and renders in <3s for 10MB file
- [x] T069 [US4] Test EPUB rendering: run `bookcat book.epub` and verify pagination works in <2s for 5MB file
- [x] T070 [US4] Test media scrolling: verify media viewers scroll with terminal output and maintain position
- [x] T071 [US4] Verify file size limits: ensure 50MB video, 10MB image, 50MB ebook limits are enforced

**Testing Guide**: See `specs/005-desktop-application/TESTING_T063-T071.md` for detailed manual testing procedures for T066-T071.

**Checkpoint**: Media viewing should work identically to web version

---

## Phase 7: User Story 5 - Image Editing with Native Tools (Priority: P2)

**Goal**: Users can edit images with drawing tools, filters, and native clipboard integration

**Independent Test**: Run `imgcat --clipboard`, edit image, copy result to clipboard, paste in Preview/Paint

### Implementation for User Story 5

- [X] T072 [P] [US5] Create clipboard module in `src-tauri/src/commands/clipboard.rs` with platform-specific implementations
- [X] T073 [US5] Implement get_clipboard_text Tauri command in `src-tauri/src/commands/clipboard.rs` using tauri-plugin-clipboard
- [X] T074 [US5] Implement set_clipboard_text Tauri command in `src-tauri/src/commands/clipboard.rs`
- [X] T075 [US5] Implement get_clipboard_image Tauri command in `src-tauri/src/commands/clipboard.rs` returning base64 PNG
- [X] T076 [US5] Implement set_clipboard_image Tauri command in `src-tauri/src/commands/clipboard.rs` accepting base64 PNG
- [X] T077 [US5] Update `static/js/image-editor.js` to call Tauri get_clipboard_image when loading from clipboard
- [X] T078 [US5] Update `static/js/image-editor.js` to call Tauri set_clipboard_image when copying edited image
- [X] T079 [US5] Test clipboard load: copy image in Preview/Paint, run `imgcat --clipboard`, verify image loads in <1s
- [ ] T080 [US5] Test clipboard copy: edit image in jterm, click "Copy to Clipboard", paste in Preview/Paint, verify edited image appears
- [ ] T081 [US5] Verify image editor service (`src/services/image_editor_service.py`) works with desktop paths
- [ ] T082 [US5] Test drawing tools: pen, arrow, text, shapes with color and stroke width customization
- [ ] T083 [US5] Test filters: blur, sharpen, brightness, contrast, saturation with real-time preview
- [ ] T084 [US5] Test undo/redo: verify 50-operation circular buffer works correctly
- [ ] T085 [US5] Test session history: verify last 20 images are accessible via `imgcat --history`
- [ ] T086 [US5] Test export: save edited image and verify PNG, JPEG, WebP, GIF, BMP formats work

**Checkpoint**: Image editing with native clipboard integration should work fully

---

## Phase 8: User Story 6 - Session Recording and Playback (Priority: P2)

**Goal**: Users can record sessions and play them back with seeking, speed control, export

**Independent Test**: Start recording, execute commands, stop recording, playback with timeline, export to ASCIINEMA

### Implementation for User Story 6

- [ ] T087 [P] [US6] Create file dialog module in `src-tauri/src/commands/file_dialogs.rs`
- [ ] T088 [US6] Implement select_file Tauri command in `src-tauri/src/commands/file_dialogs.rs` with filters for images/videos/docs
- [ ] T089 [US6] Implement select_directory Tauri command in `src-tauri/src/commands/file_dialogs.rs`
- [ ] T090 [US6] Implement save_file Tauri command in `src-tauri/src/commands/file_dialogs.rs` with filters for export formats
- [ ] T091 [US6] Verify recording service (`src/services/recording_service.py`) is bundled and works with desktop
- [ ] T092 [US6] Update recording controls in `templates/components/recording_controls.html` to use Tauri menu items
- [ ] T093 [US6] Connect "Start Recording" menu item to POST /api/v1/recordings via Python backend
- [ ] T094 [US6] Connect "Stop Recording" menu item to POST /api/v1/recordings/{id}/stop
- [ ] T095 [US6] Test recording: start recording, execute commands, verify <5% performance impact, stop recording
- [ ] T096 [US6] Test playback: select recording, verify playback with accurate timing and timeline seeking within 200ms
- [ ] T097 [US6] Test responsive playback: resize window during playback and verify 80-200 column scaling
- [ ] T098 [US6] Update export functionality to use Tauri save_file dialog instead of browser download
- [ ] T099 [US6] Test export: export recording in JSON, ASCIINEMA, HTML, TEXT formats using native save dialog
- [ ] T100 [US6] Verify 30-day retention: check cleanup job runs correctly in bundled Python backend

**Checkpoint**: Recording and playback with native file dialogs should work fully

---

## Phase 9: User Story 7 - AI Assistant Integration (Priority: P3)

**Goal**: Users can access AI assistance with voice input/output through existing Python backend

**Independent Test**: Open AI sidebar, ask question, receive response within 2-5 seconds

### Implementation for User Story 7

- [ ] T101 [US7] Verify AI service (`src/services/ai_service.py`) is bundled correctly with API client dependencies
- [ ] T102 [US7] Verify AI WebSocket handler (`src/websockets/ai_handler.py`) is accessible from Tauri WebView
- [ ] T103 [US7] Test AI sidebar: open AI assistant and verify UI loads from `templates/components/ai_sidebar.html`
- [ ] T104 [US7] Test text queries: type question, verify response within 2s (simple) or 5s (complex)
- [ ] T105 [US7] Test voice input: verify browser WebRTC speech recognition works in Tauri WebView
- [ ] T106 [US7] Test voice output: verify browser text-to-speech works in Tauri WebView
- [ ] T107 [US7] Test context awareness: verify AI uses terminal history and current directory
- [ ] T108 [US7] Test AI providers: verify OpenAI, Anthropic, Groq, Ollama configurations work
- [ ] T109 [US7] Test offline behavior: disconnect network, verify graceful error handling

**Checkpoint**: AI assistant should work identically to web version

---

## Phase 10: User Story 8 - Performance Monitoring Dashboard (Priority: P3)

**Goal**: Users can view real-time system performance metrics in a dashboard

**Independent Test**: Open performance monitor, verify CPU/memory/connection metrics update every 5 seconds

### Implementation for User Story 8

- [ ] T110 [US8] Verify performance service (`src/services/performance_service.py`) is bundled correctly
- [ ] T111 [US8] Test performance dashboard: open monitor and verify UI loads from `templates/components/performance_metrics.html`
- [ ] T112 [US8] Test metrics collection: verify CPU percentage, memory MB, active connections update every 5 seconds
- [ ] T113 [US8] Test historical charts: verify 24-hour histogram displays correctly
- [ ] T114 [US8] Test idle performance: verify desktop app CPU usage <5% idle (matching web version's 0.08%)
- [ ] T115 [US8] Test active performance: verify <15% CPU during terminal use, <25% during recording playback
- [ ] T116 [US8] Verify cleanup: check performance snapshots older than 24 hours are deleted automatically

**Checkpoint**: Performance monitoring should work identically to web version

---

## Phase 11: User Story 9 - Theme and Extension Customization (Priority: P3)

**Goal**: Users can customize appearance with themes and extend functionality with plugins

**Independent Test**: Import VS Code theme, apply it, verify colors change; install extension, verify new functionality

### Implementation for User Story 9

- [ ] T117 [US9] Verify theme service (`src/services/theme_service.py`) is bundled correctly
- [ ] T118 [US9] Verify extension service (`src/services/extension_service.py`) is bundled correctly
- [ ] T119 [US9] Add select_file dialog call to theme import in `static/js/themes.js` using Tauri command
- [ ] T120 [US9] Add select_file dialog call to extension install in `static/js/extensions.js` using Tauri command
- [ ] T121 [US9] Test theme selection: select theme from list, verify terminal colors/fonts update immediately
- [ ] T122 [US9] Test VS Code theme import: use native file dialog to select .json theme file, verify conversion and import
- [ ] T123 [US9] Test extension install: use native file dialog to select extension file, verify functionality appears
- [ ] T124 [US9] Test persistence: restart application, verify theme and extension settings persist
- [ ] T125 [US9] Verify theme/extension database records are stored in platform-specific database location

**Checkpoint**: Theme and extension customization should work with native file dialogs

---

## Phase 12: User Story 10 - Cat Commands for Development Tools (Priority: P3)

**Goal**: Users can use specialized cat commands (logcat, certcat, sqlcat, httpcat, jwtcat, wscat)

**Independent Test**: Run `sqlcat database.db`, execute query, view results, export to CSV using native save dialog

### Implementation for User Story 10

- [ ] T126 [US10] Verify cat command services are bundled correctly: log, cert, SQL, HTTP, JWT, WebSocket services
- [ ] T127 [US10] Verify cat command API endpoints are accessible from Tauri WebView
- [ ] T128 [US10] Test logcat: run `logcat app.log`, verify parsing, filtering (JSON/Apache/Nginx formats)
- [ ] T129 [US10] Test certcat: run `certcat cert.pem`, verify certificate details, chain validation, expiration
- [ ] T130 [US10] Test sqlcat: run `sqlcat database.db`, verify schema browser, query editor, pagination
- [ ] T131 [US10] Update SQL export to use Tauri save_file dialog instead of browser download
- [ ] T132 [US10] Test SQL export: export query results to CSV/JSON/XLSX using native save dialog
- [ ] T133 [US10] Test httpcat: build HTTP request, send, verify request/response inspection
- [ ] T134 [US10] Test jwtcat: decode JWT token, verify claims display and signature verification
- [ ] T135 [US10] Test wscat: connect to WebSocket server, send/receive messages, verify binary support

**Checkpoint**: All cat commands should work identically to web version with native file dialogs

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories

- [ ] T136 [P] Add get_system_info Tauri command in `src-tauri/src/commands/system.rs` returning platform, OS version, arch, hostname
- [ ] T137 [P] Add set_window_title Tauri command in `src-tauri/src/commands/system.rs` to update title with current directory
- [ ] T138 [P] Add notify Tauri command in `src-tauri/src/commands/system.rs` for system notifications
- [ ] T139 [P] Add open_external_url Tauri command in `src-tauri/src/commands/system.rs` to open links in browser
- [ ] T140 [P] Add show_in_folder Tauri command in `src-tauri/src/commands/system.rs` to reveal files in Finder/Explorer
- [ ] T141 Create database migration check in `src/main.py` to detect web→desktop migration on first launch
- [ ] T142 Implement database copy logic to migrate existing webterminal.db from project directory to platform-specific location
- [ ] T143 Add migration success notification using Tauri notify command
- [ ] T144 [P] Optimize PyInstaller bundle: add --strip flag, exclude unused modules, configure UPX compression
- [ ] T145 [P] Update `scripts/build-python.sh` to generate platform-specific executables (jterm-backend-macos, jterm-backend-windows.exe, jterm-backend-linux)
- [ ] T146 Configure code signing for macOS (requires Apple Developer account) in `scripts/package-macos.sh`
- [ ] T147 [P] Create Windows MSI installer script in `scripts/package-windows.sh`
- [ ] T148 [P] Create Linux AppImage/DEB/RPM packaging scripts in `scripts/package-linux.sh`
- [ ] T149 Implement auto-update mechanism using tauri-plugin-updater with GitHub Releases
- [ ] T150 Add error boundary handling in Tauri main.rs for Python backend crashes
- [ ] T151 Implement crash recovery: detect Python backend crash, show error dialog, offer restart
- [ ] T152 [P] Add desktop-specific documentation in `README-DESKTOP.md` covering installation, building, troubleshooting
- [ ] T153 [P] Update main `README.md` to explain web vs desktop versions
- [ ] T154 Verify all existing Python unit tests pass with bundled application
- [ ] T155 Verify all existing Jest frontend tests pass in Tauri environment
- [ ] T156 Run performance benchmarks: verify launch time <3s, CPU <5% idle, memory <200MB base
- [ ] T157 Cross-platform validation: test on macOS 10.15+, Windows 10+, Ubuntu 20.04+
- [ ] T158 Test multi-monitor support: move window between monitors with different DPI, verify rendering
- [ ] T159 Test edge cases: 50+ tabs, large files (50MB video, 10MB image), concurrent operations
- [ ] T160 Security audit: verify file validation, SSRF protection, extension sandboxing, SQL injection prevention
- [ ] T161 [P] Code cleanup: run Black on modified Python files, rustfmt on Rust files
- [ ] T162 Final build: create production installers for all platforms (DMG, MSI, AppImage)
- [ ] T163 Run quickstart.md validation: follow development setup guide, verify all steps work
- [ ] T164 Create release notes documenting desktop-specific features and migration guide

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-12)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
  - MVP = Phases 3, 4, 5 only (User Stories 1, 2, 3)
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 - Standalone Launch (P1)**: Can start after Foundational - No dependencies on other stories
- **US2 - Terminal Emulation (P1)**: Can start after Foundational - No dependencies (Python PTY reused)
- **US3 - Menu Bar (P1)**: Can start after Foundational - No dependencies
- **US4 - Media Viewing (P2)**: Can start after Foundational - No dependencies (Python services reused)
- **US5 - Image Editing (P2)**: Can start after Foundational - Depends on US4 conceptually but independently testable
- **US6 - Recording (P2)**: Can start after Foundational - No dependencies (Python services reused)
- **US7 - AI Assistant (P3)**: Can start after Foundational - No dependencies (Python services reused)
- **US8 - Performance (P3)**: Can start after Foundational - No dependencies (Python services reused)
- **US9 - Themes (P3)**: Can start after Foundational - No dependencies (Python services reused)
- **US10 - Cat Commands (P3)**: Can start after Foundational - No dependencies (Python services reused)

### Within Each User Story

- Python backend verification tasks before frontend integration tasks
- Tauri commands before UI integration
- Basic functionality before advanced features
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup Phase**: T003, T005, T007, T009, T010 can run in parallel
- **Foundational Phase**: T014, T015, T019, T020 can run in parallel
- **Once Foundational completes**: ALL user stories (US1-US10) can start in parallel if team capacity allows
- **Within each user story**: Tasks marked [P] can run in parallel
- **Polish Phase**: Most tasks (T136-T140, T144, T147-T148, T152-T153, T161) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch these tasks together (different files, no dependencies):
Task T014: Platform-specific database path resolver (src-tauri/src/utils/db_path.rs)
Task T015: Logging utility (src-tauri/src/utils/logging.rs)
Task T019: Desktop JavaScript (src-tauri/ui/desktop.js)
Task T020: Desktop CSS (src-tauri/ui/desktop.css)
```

---

## Parallel Example: User Story 5 (Image Editing)

```bash
# Launch clipboard command implementations together:
Task T073: get_clipboard_text (src-tauri/src/commands/clipboard.rs)
Task T074: set_clipboard_text (src-tauri/src/commands/clipboard.rs)
Task T075: get_clipboard_image (src-tauri/src/commands/clipboard.rs)
Task T076: set_clipboard_image (src-tauri/src/commands/clipboard.rs)
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3 Only)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T023) - CRITICAL checkpoint
3. Complete Phase 3: User Story 1 (T024-T037) - Standalone launch
4. Complete Phase 4: User Story 2 (T038-T047) - Terminal emulation
5. Complete Phase 5: User Story 3 (T048-T062) - Menu bar
6. **STOP and VALIDATE**: Test MVP independently (launch, terminal, menus work)
7. Deploy/demo if ready

**MVP Scope**: 62 tasks total for a functional desktop terminal application

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Launches!)
3. Add User Story 2 → Test independently → Deploy/Demo (Terminal works!)
4. Add User Story 3 → Test independently → Deploy/Demo (MVP complete!)
5. Add User Story 4 → Test independently → Deploy/Demo (Media viewing!)
6. Add User Story 5 → Test independently → Deploy/Demo (Image editing!)
7. Add User Story 6 → Test independently → Deploy/Demo (Recording!)
8. Continue for US7-US10 as desired → Each adds value without breaking previous stories
9. Polish phase → Production-ready release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (CRITICAL - everyone must wait for T023 completion)
2. Once Foundational is done (after T023):
   - Developer A: User Story 1 (T024-T037)
   - Developer B: User Story 2 (T038-T047)
   - Developer C: User Story 3 (T048-T062)
   - Developer D: User Story 4 (T063-T071)
   - Developer E: User Story 5 (T072-T086)
   - Etc.
3. Stories complete and integrate independently
4. Team collaborates on Polish phase (T136-T164)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Code Reuse**: 90% of codebase unchanged - most tasks are verification/integration, not new implementation
- **Python Backend**: Reused from web version (PTY, services, WebSocket handlers) - just needs bundling with PyInstaller
- **Tauri Layer**: Provides native-only features (clipboard, file dialogs, menus) - ~3,000 lines of new Rust code
- **Total Tasks**: 164 tasks organized into 13 phases (1 Setup, 1 Foundational, 10 User Stories, 1 Polish)
- **MVP**: First 62 tasks (Phases 1-5) deliver a functional desktop terminal
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: reimplementing what Python backend already does, breaking web version compatibility
