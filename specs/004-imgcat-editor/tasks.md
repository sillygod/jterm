# Tasks: imgcat Image Editor

**Input**: Design documents from `/specs/004-imgcat-editor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Following TDD approach - tests are written and verified to fail before implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project structure** (jterm existing architecture)
- Paths: `src/`, `tests/`, `templates/`, `static/` at repository root
- All tasks follow jterm's established patterns (models, services, api, websockets)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies for image editor feature

- [x] T001 Install Python dependencies (Pillow>=10.0.0, aiohttp>=3.9.0) via requirements.txt
- [x] T002 Install development dependencies (pytest-asyncio, playwright, pytest-cov) for testing
- [x] T003 [P] Install Fabric.js@5.3.0 library in static/js/vendor/ for canvas management
- [x] T004 [P] Create directory structure: templates/components/, static/js/, static/css/, tests/unit/, tests/integration/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create database migration for image editor tables in alembic/versions/YYYY_MM_DD_add_image_editor_tables.py (image_sessions, annotation_layers, edit_operations, session_history per data-model.md)
- [x] T006 Apply database migration: Run `alembic upgrade head` to create tables
- [x] T007 [P] Define ImageSession SQLAlchemy model in src/models/image_editor.py with all fields from data-model.md
- [x] T008 [P] Define AnnotationLayer SQLAlchemy model in src/models/image_editor.py with JSON field and version tracking
- [x] T009 [P] Define EditOperation SQLAlchemy model in src/models/image_editor.py for undo/redo stack
- [x] T010 [P] Define SessionHistory SQLAlchemy model in src/models/image_editor.py for history tracking
- [x] T011 Create base ImageLoaderService class in src/services/image_loader_service.py with stub methods (load_from_file, load_from_url, load_from_stdin)
- [x] T012 Create base ImageEditorService class in src/services/image_editor_service.py with stub methods (create_session, apply_filter, save_image)
- [x] T013 Create base SessionHistoryService class in src/services/session_history_service.py with stub methods (add_to_history, get_history, cleanup_expired)
- [x] T014 Create FastAPI router for image editor endpoints in src/api/image_editor_endpoints.py with placeholder routes
- [x] T015 Register image editor router in src/main.py FastAPI application

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Annotate Screenshot for Bug Report (Priority: P1) 🎯 MVP

**Goal**: Enable users to annotate screenshots with pen, arrow, text tools and copy to clipboard

**Independent Test**: Run `imgcat screenshot.png`, add annotations (pen, arrow, text), click "Copy to Clipboard", paste in Slack/email - annotations should appear on pasted image

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T016 [P] [US1] Write unit test for ImageLoaderService.load_from_file() in tests/unit/test_image_loader.py (test PNG/JPEG loading, validation, size limits)
- [x] T017 [P] [US1] Write unit test for ImageEditorService.create_session() in tests/unit/test_image_editor_service.py (test session creation, annotation layer init)
- [x] T018 [P] [US1] Write contract test for POST /api/image-editor/load in tests/contract/test_image_editor_api.py (validate against OpenAPI spec)
- [x] T019 [P] [US1] Write contract test for PUT /api/image-editor/annotation-layer in tests/contract/test_image_editor_api.py
- [x] T020 [P] [US1] Write contract test for POST /api/image-editor/export-clipboard in tests/contract/test_image_editor_api.py
- [x] T021 [US1] Write integration test for full annotation workflow in tests/integration/test_annotation_workflow.py (load → draw → export)

### Implementation for User Story 1

- [x] T022 [US1] Implement ImageLoaderService.load_from_file() in src/services/image_loader_service.py (Pillow image loading, format validation, size check, create ImageSession + temp file)
- [x] T023 [US1] Implement ImageEditorService.create_session() in src/services/image_editor_service.py (create session record, initialize empty AnnotationLayer)
- [x] T024 [US1] Implement POST /api/image-editor/load endpoint in src/api/image_editor.py (handle file source, call ImageLoaderService, return session_id and editor_url)
- [x] T025 [US1] Create base image editor HTML template in templates/components/image_editor.html (container div, toolbar placeholder, canvas container per HTMX pattern)
- [x] T026 [US1] Create toolbar HTML component in templates/components/toolbar.html (pen, arrow, text tool buttons, color picker, stroke width slider)
- [x] T027 [US1] Initialize Fabric.js canvas in static/js/image-editor.js (load image onto canvas, setup basic config, handle window resize)
- [x] T028 [P] [US1] Implement pen tool in static/js/drawing-tools.js (freehand drawing with configurable color and stroke width using Fabric.Path)
- [x] T029 [P] [US1] Implement arrow tool in static/js/drawing-tools.js (draw line with arrowhead using Fabric.Line and Fabric.Triangle)
- [x] T030 [P] [US1] Implement text tool in static/js/drawing-tools.js (click-to-add text using Fabric.IText with default styling)
- [x] T031 [US1] Implement color picker integration in static/js/drawing-tools.js (update active tool color, preview in UI)
- [x] T032 [US1] Implement stroke width controls in static/js/drawing-tools.js (slider updates active tool width, preview in UI)
- [x] T033 [US1] Implement annotation persistence in src/services/image_editor_service.py (save canvas JSON to AnnotationLayer, increment version for optimistic locking)
- [x] T034 [US1] Implement PUT /api/image-editor/annotation-layer endpoint in src/api/image_editor.py (receive Fabric.js JSON, store via ImageEditorService, return new version)
- [x] T035 [US1] Implement canvas auto-save in static/js/image-editor.js (debounce 500ms, serialize canvas JSON, PUT to annotation-layer endpoint)
- [x] T036 [US1] Implement clipboard export in static/js/clipboard-handler.js (canvas.toDataURL('image/png'), create Blob, request clipboard permissions, navigator.clipboard.write)
- [x] T037 [US1] Implement POST /api/image-editor/export-clipboard endpoint in src/api/image_editor.py (prepare temp URL for clipboard operation, 30s expiry)
- [x] T038 [US1] Add "Copy to Clipboard" button to toolbar in templates/components/toolbar.html (wire to clipboard-handler.js)
- [x] T039 [US1] Implement undo/redo state snapshots in static/js/image-editor.js (circular buffer of 50 Fabric.js JSON snapshots, position pointer)
- [x] T040 [US1] Implement EditOperation storage in src/services/image_editor_service.py (store snapshot on each edit, maintain position 0-49)
- [x] T041 [US1] Implement POST /api/image-editor/undo endpoint in src/api/image_editor.py (load previous snapshot by position, return canvas JSON)
- [x] T042 [US1] Implement POST /api/image-editor/redo endpoint in src/api/image_editor.py (load next snapshot by position, return canvas JSON)
- [x] T043 [US1] Add undo/redo buttons to toolbar in templates/components/toolbar.html (Cmd+Z / Cmd+Shift+Z keyboard shortcuts)
- [x] T044 [US1] Implement undo/redo logic in static/js/image-editor.js (load snapshot from API, canvas.loadFromJSON, update position, clear redo on new edit)
- [x] T045 [US1] Add error handling for image load failures in src/services/image_loader_service.py (corrupt files, unsupported formats, size exceeded)
- [x] T046 [US1] Add error handling UI in static/js/image-editor.js (display error messages, suggest corrective actions)
- [x] T047 [US1] Add CSS styling for editor UI in static/css/image-editor.css (toolbar layout, canvas container, button states, responsive design)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Users can annotate images and copy to clipboard.

---

## Phase 4: User Story 2 - Edit Image from Clipboard (Priority: P1)

**Goal**: Enable loading images directly from clipboard via `pbpaste | imgcat` or `imgcat --clipboard`

**Independent Test**: Copy image to clipboard (screenshot tool), run `imgcat --clipboard`, verify editor opens with clipboard image, make edits, copy back to clipboard, paste in external app

### Tests for User Story 2

- [x] T048 [P] [US2] Write unit test for ImageLoaderService.load_from_stdin() in tests/unit/test_image_loader.py (test clipboard data parsing, PNG/JPEG detection)
- [x] T049 [P] [US2] Write unit test for clipboard source handling in tests/unit/test_image_editor_service.py (test session creation with clipboard source)
- [x] T050 [US2] Write integration test for clipboard workflow in tests/integration/test_clipboard_workflow.py (stdin → load → edit → save prompts filename)

### Implementation for User Story 2

- [ ] T051 [US2] Implement ImageLoaderService.load_from_stdin() in src/services/image_loader_service.py (detect stdin image data, parse format, save to temp file, create ImageSession with source_type='clipboard')
- [ ] T052 [US2] Add `--clipboard` flag handling to imgcat CLI in src/cli/imgcat.py (read clipboard via platform-specific utility: pbpaste/xclip/clip.exe)
- [ ] T053 [US2] Add stdin detection to POST /api/image-editor/load in src/api/image_editor.py (check for clipboard_data in request, call load_from_stdin)
- [ ] T054 [US2] Implement platform detection in src/services/image_loader_service.py (sys.platform check, suggest appropriate clipboard utility if missing)
- [ ] T055 [US2] Update clipboard copy handler in static/js/clipboard-handler.js (handle clipboard sources, notify user if clipboard copy succeeds)
- [ ] T056 [US2] Implement save dialog for clipboard sources in templates/components/image_editor.html (prompt for filename, suggest default based on timestamp)
- [ ] T057 [US2] Update POST /api/image-editor/save endpoint in src/api/image_editor.py (require output_path for clipboard sources, validate path, save via ImageEditorService)
- [ ] T058 [US2] Implement ImageEditorService.save_image() in src/services/image_editor_service.py (apply canvas to image using Pillow, save to file system, update ImageSession.is_modified=False)
- [ ] T059 [US2] Add empty clipboard detection in src/services/image_loader_service.py (detect empty stdin, return error FR-025)
- [ ] T060 [US2] Add clipboard permission error handling in static/js/clipboard-handler.js (catch NotAllowedError, show permission prompt)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Users can load from files or clipboard.

---

## Phase 5: User Story 3 - Crop and Resize Images (Priority: P1)

**Goal**: Enable cropping and resizing images for documentation and sharing

**Independent Test**: Open image, select crop tool, drag rectangle around region, click "Apply Crop", verify crop applied. Select "Resize", enter dimensions with aspect ratio lock, verify resize applied.

### Tests for User Story 3

- [ ] T061 [P] [US3] Write unit test for ImageEditorService.crop_image() in tests/unit/test_image_editor_service.py (test Pillow crop operation, boundary validation)
- [ ] T062 [P] [US3] Write unit test for ImageEditorService.resize_image() in tests/unit/test_image_editor_service.py (test Pillow resize, aspect ratio calculation)
- [ ] T063 [US3] Write integration test for crop and resize in tests/integration/test_crop_resize.py (load → crop → resize → save)

### Implementation for User Story 3

- [ ] T064 [P] [US3] Implement crop tool UI in static/js/drawing-tools.js (Fabric.Rect selection with draggable handles, dim outside area, "Apply Crop" button)
- [ ] T065 [P] [US3] Implement resize dialog in templates/components/image_editor.html (width/height inputs, aspect ratio lock checkbox, preview dimensions, "Apply Resize" button)
- [ ] T066 [US3] Implement ImageEditorService.crop_image() in src/services/image_editor_service.py (Pillow Image.crop, update ImageSession dimensions, update canvas size)
- [ ] T067 [US3] Implement ImageEditorService.resize_image() in src/services/image_editor_service.py (Pillow Image.resize with LANCZOS filter, aspect ratio calculation if locked, update ImageSession dimensions)
- [ ] T068 [US3] Add crop operation to POST /api/image-editor/process endpoint in src/api/image_editor.py (receive crop bounds, call ImageEditorService.crop_image, return processed image URL)
- [ ] T069 [US3] Add resize operation to POST /api/image-editor/process endpoint in src/api/image_editor.py (receive dimensions and aspect_ratio flag, call ImageEditorService.resize_image, return processed image URL)
- [ ] T070 [US3] Wire crop tool to API in static/js/drawing-tools.js (get selection bounds, POST to /api/image-editor/process, reload canvas with cropped image)
- [ ] T071 [US3] Wire resize dialog to API in static/js/image-editor.js (calculate dimensions, POST to /api/image-editor/process, reload canvas with resized image)
- [ ] T072 [US3] Add crop/resize to undo/redo stack in static/js/image-editor.js (store pre-crop/resize canvas state, enable undo to revert)
- [ ] T073 [US3] Update canvas dimensions after crop/resize in static/js/image-editor.js (Fabric.Canvas.setDimensions, re-render annotations)

**Checkpoint**: All three P1 user stories should now be independently functional. MVP is complete - users can annotate, use clipboard, and crop/resize.

---

## Phase 6: User Story 4 - Apply Filters and Adjustments (Priority: P2)

**Goal**: Enable brightness, contrast, saturation adjustments (client-side) and blur, sharpen filters (server-side)

**Independent Test**: Open image, select "Brightness" adjustment, move slider, verify live preview, click "Apply", verify brightness changed. Select "Blur" filter, adjust intensity, click "Apply", verify server-processed blur applied.

### Tests for User Story 4

- [ ] T074 [P] [US4] Write unit test for client-side filter preview in tests/unit/test_filter_engine.js (Jest test for CSS filter application)
- [ ] T075 [P] [US4] Write unit test for ImageEditorService.apply_blur() in tests/unit/test_image_editor_service.py (test Pillow GaussianBlur)
- [ ] T076 [P] [US4] Write unit test for ImageEditorService.apply_sharpen() in tests/unit/test_image_editor_service.py (test Pillow UnsharpMask)
- [ ] T077 [US4] Write integration test for filter workflow in tests/integration/test_filters.py (load → adjust brightness → apply blur → save)

### Implementation for User Story 4

- [ ] T078 [P] [US4] Create filter panel HTML in templates/components/filter_panel.html (brightness/contrast/saturation sliders, blur/sharpen controls, "Apply" and "Reset All" buttons)
- [ ] T079 [P] [US4] Implement client-side brightness adjustment in static/js/filter-engine.js (CSS filter: brightness, live preview on slider change, <200ms update)
- [ ] T080 [P] [US4] Implement client-side contrast adjustment in static/js/filter-engine.js (CSS filter: contrast, live preview)
- [ ] T081 [P] [US4] Implement client-side saturation adjustment in static/js/filter-engine.js (CSS filter: saturate, live preview)
- [ ] T082 [US4] Implement filter apply logic in static/js/filter-engine.js (on "Apply" click, commit CSS filters to canvas using canvas filters API, clear preview CSS)
- [ ] T083 [US4] Implement ImageEditorService.apply_blur() in src/services/image_editor_service.py (Pillow ImageFilter.GaussianBlur with radius parameter)
- [ ] T084 [US4] Implement ImageEditorService.apply_sharpen() in src/services/image_editor_service.py (Pillow ImageFilter.UnsharpMask with intensity parameter)
- [ ] T085 [US4] Add blur operation to POST /api/image-editor/process endpoint in src/api/image_editor.py (receive radius param, call apply_blur, return processed image URL)
- [ ] T086 [US4] Add sharpen operation to POST /api/image-editor/process endpoint in src/api/image_editor.py (receive intensity param, call apply_sharpen, return processed image URL)
- [ ] T087 [US4] Wire blur/sharpen controls to API in static/js/filter-engine.js (POST to /api/image-editor/process, show loading indicator, reload canvas with filtered image)
- [ ] T088 [US4] Implement "Reset All" button logic in static/js/filter-engine.js (clear all CSS filters, reload original image, reset sliders to default)
- [ ] T089 [US4] Add filter operations to undo/redo stack in static/js/image-editor.js (store pre-filter canvas state)
- [ ] T090 [US4] Add loading indicator for server-side filters in templates/components/filter_panel.html (spinner during blur/sharpen processing)

**Checkpoint**: User Story 4 complete. Users can now adjust image quality and apply filters.

---

## Phase 7: User Story 5 - Edit Previously Displayed Images (Priority: P2)

**Goal**: Enable quick re-editing of images from session history via `imgcat --history` or `imgcat -e N`

**Independent Test**: View 3 images with imgcat in a terminal session. Run `imgcat --history`, verify list shows 3 entries. Run `imgcat -e 2`, verify second most recent image opens in editor.

### Tests for User Story 5

- [ ] T091 [P] [US5] Write unit test for SessionHistoryService.add_to_history() in tests/unit/test_session_history_service.py (test LRU eviction, 20-item limit)
- [ ] T092 [P] [US5] Write unit test for SessionHistoryService.get_history() in tests/unit/test_session_history_service.py (test ordered retrieval, terminal session filtering)
- [ ] T093 [US5] Write integration test for history workflow in tests/integration/test_history.py (view multiple images → retrieve history → reopen from history)

### Implementation for User Story 5

- [ ] T094 [US5] Implement SessionHistoryService.add_to_history() in src/services/session_history_service.py (OrderedDict LRU cache, upsert to SQLite session_history table, 20-item eviction)
- [ ] T095 [US5] Implement SessionHistoryService.get_history() in src/services/session_history_service.py (query SQLite by terminal_session_id, order by last_viewed_at DESC, limit 20)
- [ ] T096 [US5] Update POST /api/image-editor/load to call add_to_history() in src/api/image_editor.py (after successful load, add to SessionHistory)
- [ ] T097 [US5] Implement GET /api/image-editor/history endpoint in src/api/image_editor.py (receive terminal_session_id, call SessionHistoryService.get_history, return JSON array)
- [ ] T098 [US5] Implement POST /api/image-editor/history/{entry_id}/reopen endpoint in src/api/image_editor.py (load image from history entry, create new ImageSession, return session_id and editor_url)
- [ ] T099 [US5] Add `--history` flag to imgcat CLI in src/cli/imgcat.py (call GET /api/image-editor/history, display numbered list, prompt for selection)
- [ ] T100 [US5] Add `-e N` flag to imgcat CLI in src/cli/imgcat.py (call GET /api/image-editor/history, select Nth entry, call reopen endpoint)
- [ ] T101 [US5] Add `--edit-last` flag to imgcat CLI in src/cli/imgcat.py (shortcut for `-e 1`, reopen most recent image)
- [ ] T102 [US5] Implement history cache restoration in src/services/session_history_service.py (load from SQLite on server start, populate in-memory OrderedDict)
- [ ] T103 [US5] Implement cleanup job in src/services/session_history_service.py (background task to delete history entries older than 7 days, schedule via FastAPI lifespan)
- [ ] T104 [US5] Add empty history handling in src/cli/imgcat.py (display message "No images in session history" when history is empty)

**Checkpoint**: User Story 5 complete. Power users can quickly re-edit recent images without retyping paths.

---

## Phase 8: User Story 6 - Load and Edit Images from URLs (Priority: P3)

**Goal**: Enable loading images directly from HTTP/HTTPS URLs

**Independent Test**: Run `imgcat https://example.com/screenshot.png`, verify image downloads and opens in editor, make edits, save (prompts for filename).

### Tests for User Story 6

- [ ] T105 [P] [US6] Write unit test for ImageLoaderService.load_from_url() in tests/unit/test_image_loader.py (test aiohttp download, timeout, size limits)
- [ ] T106 [P] [US6] Write unit test for URL validation in tests/unit/test_image_loader.py (test HTTP/HTTPS only, invalid URLs)
- [ ] T107 [US6] Write integration test for URL loading in tests/integration/test_url_loading.py (load from URL → edit → save prompts filename)

### Implementation for User Story 6

- [ ] T108 [US6] Implement ImageLoaderService.load_from_url() in src/services/image_loader_service.py (aiohttp.ClientSession, stream download, 50MB limit, 10s timeout, save to temp file, create ImageSession with source_type='url')
- [ ] T109 [US6] Add URL validation in src/services/image_loader_service.py (whitelist HTTP/HTTPS schemes, reject private IPs, validate Content-Type header)
- [ ] T110 [US6] Add URL source handling to POST /api/image-editor/load in src/api/image_editor.py (check for source_type='url', call load_from_url, show progress indicator)
- [ ] T111 [US6] Implement loading indicator for URL downloads in templates/components/image_editor.html (display "Loading image from URL..." during download)
- [ ] T112 [US6] Add URL timeout error handling in src/services/image_loader_service.py (catch aiohttp.ClientTimeout, return error message FR-003)
- [ ] T113 [US6] Add URL load failure handling in src/api/image_editor.py (catch connection errors, invalid URLs, return user-friendly error messages)
- [ ] T114 [US6] Update save dialog for URL sources in templates/components/image_editor.html (suggest filename from URL path, e.g., "screenshot.png" from URL)
- [ ] T115 [US6] Add SSRF prevention in src/services/image_loader_service.py (block private IP ranges: 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)

**Checkpoint**: User Story 6 complete. Users can now load images from web URLs for editing.

---

## Phase 9: User Story 7 - Advanced Drawing and Shapes (Priority: P2)

**Goal**: Enable drawing rectangles, circles, lines with customizable colors, stroke widths, and fill options

**Independent Test**: Open image, select rectangle tool, drag to draw rectangle with default stroke. Click color picker, change color, verify next rectangle uses new color. Select circle tool, toggle "Fill", verify circle drawn as filled. Select line tool, hold Shift, verify line snaps to 45° angles.

### Tests for User Story 7

- [ ] T116 [P] [US7] Write unit test for shape tool logic in tests/unit/test_drawing_tools.js (Jest test for rectangle, circle, line creation)
- [ ] T117 [US7] Write integration test for advanced shapes in tests/integration/test_shapes.py (draw multiple shapes → customize → select → move → delete)

### Implementation for User Story 7

- [ ] T118 [P] [US7] Implement rectangle tool in static/js/drawing-tools.js (Fabric.Rect, drag to create, use active stroke color and width)
- [ ] T119 [P] [US7] Implement circle tool in static/js/drawing-tools.js (Fabric.Circle, drag from center, support fill toggle)
- [ ] T120 [P] [US7] Implement line tool in static/js/drawing-tools.js (Fabric.Line, drag to create, Shift key snaps to 45° angles)
- [ ] T121 [US7] Add fill toggle control to toolbar in templates/components/toolbar.html (checkbox for "Fill Shape", applies to circle and rectangle)
- [ ] T122 [US7] Implement fill toggle logic in static/js/drawing-tools.js (update shape fill property based on toggle state)
- [ ] T123 [US7] Implement selection tool in static/js/drawing-tools.js (enable Fabric.js object selection, show bounding box with handles)
- [ ] T124 [US7] Implement shape manipulation in static/js/image-editor.js (move selected shape via drag, resize via handles, delete via Delete key)
- [ ] T125 [US7] Add shape drawing to undo/redo stack in static/js/image-editor.js (store canvas state after shape creation)
- [ ] T126 [US7] Update toolbar to show active tool state in templates/components/toolbar.html (highlight selected tool button)

**Checkpoint**: User Story 7 complete. Users can now draw professional-looking shapes with customization.

---

## Phase 10: User Story 8 - Text Annotations with Formatting (Priority: P2)

**Goal**: Enable text annotations with font size, color, bold, italic, and background customization

**Independent Test**: Open image, select text tool, click to add text, type "Bug here", select font size 24pt from dropdown, verify text appears at 24pt. Click bold button, verify text becomes bold. Enable "Text Background", choose yellow, verify text has yellow background for contrast.

### Tests for User Story 8

- [ ] T127 [P] [US8] Write unit test for text formatting logic in tests/unit/test_drawing_tools.js (Jest test for font size, color, bold, italic, background)
- [ ] T128 [US8] Write integration test for text formatting in tests/integration/test_text_formatting.py (add text → format → edit → save)

### Implementation for User Story 8

- [ ] T129 [P] [US8] Add font size dropdown to toolbar in templates/components/toolbar.html (12pt, 14pt, 16pt, 18pt, 20pt, 24pt, 28pt, 32pt, 48pt, 64pt, 72pt options)
- [ ] T130 [P] [US8] Add text formatting buttons to toolbar in templates/components/toolbar.html (Bold, Italic, Text Background checkbox with color picker)
- [ ] T131 [US8] Implement font size control in static/js/drawing-tools.js (update Fabric.IText fontSize property, apply to new text or selected text)
- [ ] T132 [US8] Implement bold formatting in static/js/drawing-tools.js (update Fabric.IText fontWeight property, toggle 'normal'/'bold')
- [ ] T133 [US8] Implement italic formatting in static/js/drawing-tools.js (update Fabric.IText fontStyle property, toggle 'normal'/'italic')
- [ ] T134 [US8] Implement text background in static/js/drawing-tools.js (add Fabric.Rect behind text with backgroundColor, bind to text position)
- [ ] T135 [US8] Implement text editing in static/js/image-editor.js (double-click text to edit content, update format controls to match selected text)
- [ ] T136 [US8] Update text tool to apply current format settings in static/js/drawing-tools.js (new text uses active font size, bold, italic, background)
- [ ] T137 [US8] Add text formatting to undo/redo stack in static/js/image-editor.js (store canvas state after text formatting changes)

**Checkpoint**: All user stories complete. Feature is fully functional with all P1, P2, and P3 capabilities.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final refinements

- [ ] T138 [P] Add comprehensive error handling across all services in src/services/ (log errors, return user-friendly messages, handle edge cases from spec.md)
- [ ] T139 [P] Add security hardening: path validation in src/services/image_loader_service.py (prevent directory traversal, validate file extensions)
- [ ] T140 [P] Add security hardening: SQL injection prevention in src/services/ (verify parameterized queries, validate UUIDs)
- [ ] T141 [P] Implement cleanup job for expired sessions in src/services/image_editor_service.py (delete image_sessions older than 24 hours, background task)
- [ ] T142 [P] Implement cleanup job for temporary files in src/services/image_editor_service.py (delete orphaned temp files from temp_file_path)
- [ ] T143 [P] Add performance optimization: image downsampling in src/services/image_editor_service.py (downsample large images for editing, upsample on save)
- [ ] T144 [P] Add performance optimization: canvas JSON compression in src/services/image_editor_service.py (gzip compress snapshots before storing in edit_operations)
- [ ] T145 [P] Write E2E test for full user journey in tests/e2e/test_editor_e2e.py (Playwright: load image → annotate → crop → apply filter → save → verify file)
- [ ] T146 [P] Add logging for all image editor operations in src/services/ (structured logging with log levels, include session_id and operation_type)
- [ ] T147 [P] Update CLAUDE.md with feature documentation (add imgcat editor to "Recent Changes" section, document new commands)
- [ ] T148 [P] Create user documentation in docs/imgcat-editor.md (usage examples, keyboard shortcuts, troubleshooting)
- [ ] T149 Run quickstart.md manual testing validation (follow quickstart.md test scenarios, verify all workflows function correctly)
- [ ] T150 Performance benchmarking (verify SC-001 through SC-010 success criteria met, document results)
- [ ] T151 Security audit (review SSRF prevention, path validation, clipboard permissions, file size limits)
- [ ] T152 Code review and refactoring (extract common patterns, improve naming, add inline comments for complex logic)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-10)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order: US1 (P1) → US2 (P1) → US3 (P1) → US4 (P2) → US5 (P2) → US7 (P2) → US8 (P2) → US6 (P3)
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Independent, extends US1 loader (no blocking dependency)
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Independent, uses existing canvas and services
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Independent, adds filters without blocking other stories
- **User Story 5 (P2)**: Can start after Foundational (Phase 2) - Independent, adds history tracking (integrates with loader but non-blocking)
- **User Story 6 (P3)**: Can start after Foundational (Phase 2) - Independent, extends loader with URL support
- **User Story 7 (P2)**: Can start after Foundational (Phase 2) - Independent, extends drawing tools
- **User Story 8 (P2)**: Can start after Foundational (Phase 2) - Independent, extends text tool from US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD approach per plan.md Constitution Check)
- Models before services (T007-T010 before T011-T013)
- Services before endpoints (T011-T013 before T014)
- Backend endpoints before frontend (e.g., T024 before T027)
- Core implementation before integration (e.g., T022-T024 before T034)
- Story complete and tested before moving to next priority

### Parallel Opportunities

- **Setup Phase**: All tasks marked [P] can run in parallel (T003, T004)
- **Foundational Phase**: T007-T010 (models) can run in parallel
- **Per User Story**: All tests marked [P] can run in parallel (e.g., T016-T020 for US1)
- **Per User Story**: Models/services marked [P] within story can run in parallel (e.g., T028-T030 drawing tools for US1)
- **Cross-Story**: Different user stories can be worked on in parallel by different team members after Foundational phase completes
- **Polish Phase**: T138-T148 can run in parallel (independent improvements)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (write and verify they FAIL):
Task T016: "Write unit test for ImageLoaderService.load_from_file() in tests/unit/test_image_loader.py"
Task T017: "Write unit test for ImageEditorService.create_session() in tests/unit/test_image_editor_service.py"
Task T018: "Write contract test for POST /api/image-editor/load in tests/contract/test_image_editor_api.py"
Task T019: "Write contract test for PUT /api/image-editor/annotation-layer in tests/contract/test_image_editor_api.py"
Task T020: "Write contract test for POST /api/image-editor/export-clipboard in tests/contract/test_image_editor_api.py"

# After tests written and failing, launch parallel implementation:
Task T028: "Implement pen tool in static/js/drawing-tools.js"
Task T029: "Implement arrow tool in static/js/drawing-tools.js"
Task T030: "Implement text tool in static/js/drawing-tools.js"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 3 - All P1)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T015) - CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T016-T047) - Core annotation workflow
4. Complete Phase 4: User Story 2 (T048-T060) - Clipboard support
5. Complete Phase 5: User Story 3 (T061-T073) - Crop/resize
6. **STOP and VALIDATE**: Test all P1 stories independently and together
7. Deploy/demo MVP if ready

**MVP delivers**: Complete image annotation workflow with file and clipboard loading, annotations (pen/arrow/text), undo/redo, copy to clipboard, crop, and resize. All core acceptance scenarios met.

### Incremental Delivery (P2 and P3 Stories)

After MVP:
1. Add User Story 4 (Filters - T074-T090) → Test independently → Deploy/Demo
2. Add User Story 5 (History - T091-T104) → Test independently → Deploy/Demo
3. Add User Story 7 (Shapes - T116-T126) → Test independently → Deploy/Demo
4. Add User Story 8 (Text Formatting - T127-T137) → Test independently → Deploy/Demo
5. Add User Story 6 (URL Loading - T105-T115) → Test independently → Deploy/Demo
6. Complete Phase 11 (Polish - T138-T152) → Final validation

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T015)
2. Once Foundational is done:
   - Developer A: User Story 1 (T016-T047)
   - Developer B: User Story 2 (T048-T060)
   - Developer C: User Story 3 (T061-T073)
3. After P1 stories integrate and validate:
   - Developer A: User Story 4 (T074-T090)
   - Developer B: User Story 5 (T091-T104)
   - Developer C: User Story 7 (T116-T126)
4. Continue parallel development through P2/P3 stories
5. Team converges for Polish phase (T138-T152)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- TDD approach: Write tests FIRST, verify they FAIL, then implement
- Commit after each task or logical group (e.g., all tests for a story)
- Stop at any checkpoint to validate story independently
- Performance targets: Image load <1s, canvas ops <50ms, undo/redo <100ms, filter preview <200ms
- Security: Validate paths, sanitize URLs, enforce 50MB limit, prevent SSRF
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Total Task Count: 152 tasks

- Setup: 4 tasks
- Foundational: 11 tasks
- User Story 1 (P1): 32 tasks
- User Story 2 (P1): 13 tasks
- User Story 3 (P1): 13 tasks
- User Story 4 (P2): 17 tasks
- User Story 5 (P2): 14 tasks
- User Story 6 (P3): 11 tasks
- User Story 7 (P2): 11 tasks
- User Story 8 (P2): 11 tasks
- Polish: 15 tasks

**MVP Scope** (P1 stories only): 73 tasks (Setup + Foundational + US1 + US2 + US3)
