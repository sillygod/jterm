# Developer Quickstart: imgcat Image Editor

**Branch**: `004-imgcat-editor` | **Date**: 2025-11-12
**Purpose**: Get developers up and running with image editor development

## Prerequisites

- Python 3.11+ installed
- Node.js 18+ (for frontend testing)
- jterm repository cloned
- Virtual environment activated

## Initial Setup

### 1. Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt
pip install Pillow>=10.0.0 aiohttp>=3.9.0

# Development dependencies
pip install pytest-asyncio playwright pytest-cov

# Frontend dependencies (for testing)
npm install  # If package.json exists, otherwise skip
```

### 2. Database Migration

```bash
# Generate migration for new tables
alembic revision --autogenerate -m "Add image editor tables"

# Review generated migration in alembic/versions/
# Verify tables: image_sessions, annotation_layers, edit_operations, session_history

# Apply migration
alembic upgrade head
```

### 3. Verify Setup

```bash
# Run existing tests to ensure nothing broke
pytest tests/unit/

# Check database tables created
sqlite3 jterm.db ".tables" | grep image
# Should show: image_sessions, annotation_layers, edit_operations, session_history
```

---

## Development Workflow

### Test-First Development (TDD)

**IMPORTANT**: Follow strict TDD process:

1. **Write Tests First** (Red)
   - Write unit test for specific functionality
   - Test should fail (function doesn't exist yet)

2. **Implement Minimum Code** (Green)
   - Write just enough code to make test pass
   - Don't add extra features

3. **Refactor** (Refactor)
   - Clean up code while keeping tests green
   - Extract common logic, improve naming

**Example TDD Cycle**:

```python
# Step 1: Write test (Red)
# tests/unit/test_image_loader.py
def test_load_from_file_creates_session():
    loader = ImageLoaderService()
    session = await loader.load_from_file("/path/to/test.png", "terminal_123")
    assert session.image_format == "png"
    assert session.image_source_type == "file"

# Run test: pytest tests/unit/test_image_loader.py::test_load_from_file_creates_session
# ❌ FAILS - ImageLoaderService doesn't exist

# Step 2: Implement (Green)
# src/services/image_loader_service.py
class ImageLoaderService:
    async def load_from_file(self, path: str, terminal_id: str):
        # Minimum implementation to pass test
        return ImageSession(
            image_format="png",
            image_source_type="file",
            # ... other fields
        )

# Run test again
# ✅ PASSES

# Step 3: Refactor
# Extract validation, add error handling, etc.
```

---

## Project Structure

```
src/
├── models/
│   └── image_editor.py         # SQLAlchemy models
├── services/
│   ├── image_editor_service.py # Core editing logic
│   ├── image_loader_service.py # Image loading
│   └── session_history_service.py # History management
├── api/
│   └── image_editor.py         # FastAPI endpoints
└── websockets/
    └── image_editor.py         # WebSocket handler (Phase 2)

templates/
└── components/
    └── image_editor.html       # HTMX editor UI

static/
├── js/
│   ├── image-editor.js         # Main editor logic
│   ├── drawing-tools.js        # Tool implementations
│   └── filter-engine.js        # Client-side filters
└── css/
    └── image-editor.css        # Styling

tests/
├── unit/                       # Fast, isolated tests
├── integration/                # Feature workflow tests
├── contract/                   # API contract tests
└── e2e/                        # Browser tests (Playwright)
```

---

## Development Tasks by Phase

### Phase 1: Core Infrastructure (P1 Foundation)

**Goal**: Set up models, services, and basic API endpoints

1. **Models** (`src/models/image_editor.py`)
   - [ ] Define ImageSession, AnnotationLayer, EditOperation, SessionHistory
   - [ ] Add SQLAlchemy relationships
   - [ ] Write model unit tests

2. **Image Loader Service** (`src/services/image_loader_service.py`)
   - [ ] Implement `load_from_file()`
   - [ ] Implement `load_from_url()` (with aiohttp)
   - [ ] Implement `load_from_stdin()` (clipboard)
   - [ ] Add image validation (format, size limits)
   - [ ] Write service unit tests

3. **Basic API Endpoints** (`src/api/image_editor.py`)
   - [ ] POST `/api/image-editor/load`
   - [ ] GET `/api/image-editor/session/{id}`
   - [ ] DELETE `/api/image-editor/session/{id}`
   - [ ] Write contract tests

**Testing Checklist**:
- [ ] All unit tests pass
- [ ] API contract tests match OpenAPI spec
- [ ] Manual test: `imgcat test.png` loads image

---

### Phase 2: Annotation & Canvas (User Story 1)

**Goal**: Implement drawing tools and canvas management

1. **Frontend Canvas Setup** (`static/js/image-editor.js`)
   - [ ] Initialize Fabric.js canvas
   - [ ] Load image onto canvas
   - [ ] Set up canvas event handlers

2. **Drawing Tools** (`static/js/drawing-tools.js`)
   - [ ] Pen tool (freehand drawing)
   - [ ] Arrow tool
   - [ ] Text tool (basic, no formatting yet)
   - [ ] Color picker integration
   - [ ] Stroke width controls

3. **Annotation Persistence** (`src/services/image_editor_service.py`)
   - [ ] Save canvas JSON to AnnotationLayer
   - [ ] Load canvas JSON from database
   - [ ] Version tracking (optimistic locking)

4. **API Endpoints**
   - [ ] PUT `/api/image-editor/annotation-layer`
   - [ ] Write integration tests

**Testing Checklist**:
- [ ] Can draw with pen tool
- [ ] Can add arrows
- [ ] Can add text
- [ ] Canvas state persists on page refresh
- [ ] Integration test: Full annotation workflow

---

### Phase 3: Clipboard & Export (User Stories 1 & 2)

**Goal**: Copy to clipboard and save functionality

1. **Clipboard Handler** (`static/js/clipboard-handler.js`)
   - [ ] Request clipboard permissions
   - [ ] Export canvas to PNG blob
   - [ ] Use Clipboard API to write image
   - [ ] Handle permission errors

2. **Save Functionality** (`src/api/image_editor.py`)
   - [ ] POST `/api/image-editor/save`
   - [ ] Apply canvas annotations to image (Pillow)
   - [ ] Save to file system
   - [ ] Handle permission errors

3. **Clipboard Input** (`src/services/image_loader_service.py`)
   - [ ] Detect stdin image data
   - [ ] Parse clipboard formats (PNG, JPEG)
   - [ ] Create temporary file

**Testing Checklist**:
- [ ] Copy to clipboard button works
- [ ] Can paste into external apps (Slack, etc.)
- [ ] Save prompts for filename (clipboard sources)
- [ ] `pbpaste | imgcat` workflow functional
- [ ] E2E test: Screenshot → annotate → copy → paste

---

### Phase 4: Undo/Redo (User Story 1, Part 2)

**Goal**: Implement operation history

1. **Edit Operation Storage** (`src/services/image_editor_service.py`)
   - [ ] Store canvas snapshots after each edit
   - [ ] Circular buffer logic (50 operations max)
   - [ ] Position tracking

2. **Undo/Redo API** (`src/api/image_editor.py`)
   - [ ] POST `/api/image-editor/undo`
   - [ ] POST `/api/image-editor/redo`

3. **Frontend Undo/Redo** (`static/js/image-editor.js`)
   - [ ] Undo button handler
   - [ ] Redo button handler
   - [ ] Keyboard shortcuts (Cmd+Z, Cmd+Shift+Z)
   - [ ] Clear redo stack on new operation

**Testing Checklist**:
- [ ] Undo reverts last operation
- [ ] Can undo up to 50 operations
- [ ] Redo works after undo
- [ ] New operation clears redo stack
- [ ] Performance: Undo/redo <100ms

---

### Phase 5: Crop & Resize (User Story 3)

**Goal**: Basic image transformations

1. **Crop Tool** (`static/js/drawing-tools.js`)
   - [ ] Selection rectangle with draggable handles
   - [ ] Dim area outside selection
   - [ ] Apply crop button

2. **Resize Dialog** (`templates/components/image_editor.html`)
   - [ ] Width/height input fields
   - [ ] Aspect ratio lock checkbox
   - [ ] Preview dimensions

3. **Backend Processing** (`src/services/image_editor_service.py`)
   - [ ] Crop image with Pillow
   - [ ] Resize image with Pillow (LANCZOS filter)
   - [ ] Update canvas dimensions

**Testing Checklist**:
- [ ] Can select crop region
- [ ] Crop applies correctly
- [ ] Resize maintains aspect ratio when locked
- [ ] Integration test: Load → crop → save

---

### Phase 6: Filters (User Story 4, P2)

**Goal**: Brightness/contrast/blur/sharpen

1. **Client-Side Filters** (`static/js/filter-engine.js`)
   - [ ] Brightness adjustment (CSS filter)
   - [ ] Contrast adjustment (CSS filter)
   - [ ] Live preview with sliders
   - [ ] Apply button (commits to canvas)

2. **Server-Side Filters** (`src/api/image_editor.py`)
   - [ ] POST `/api/image-editor/process`
   - [ ] Implement blur (Pillow ImageFilter.GaussianBlur)
   - [ ] Implement sharpen (Pillow ImageFilter.UnsharpMask)

3. **Filter Panel UI** (`templates/components/filter_panel.html`)
   - [ ] Slider controls
   - [ ] Reset All button
   - [ ] Loading indicator for server operations

**Testing Checklist**:
- [ ] Brightness preview updates in <200ms
- [ ] Blur completes in <2s (5MB image)
- [ ] Reset All clears all filters
- [ ] Filters combine correctly

---

### Phase 7: Session History (User Story 5, P2)

**Goal**: Quick re-editing from history

1. **History Service** (`src/services/session_history_service.py`)
   - [ ] Add to history on image view
   - [ ] LRU eviction (20-item limit)
   - [ ] SQLite persistence + in-memory cache

2. **History API** (`src/api/image_editor.py`)
   - [ ] GET `/api/image-editor/history`
   - [ ] POST `/api/image-editor/history/{id}/reopen`

3. **CLI Integration**
   - [ ] `imgcat --history` command
   - [ ] `imgcat -e N` command (reopen Nth entry)

**Testing Checklist**:
- [ ] History limited to 20 entries
- [ ] Oldest entry evicted (LRU)
- [ ] History persists across browser refresh
- [ ] Cleanup job removes old entries (>7 days)

---

### Phase 8: Advanced Features (P2/P3)

**Later phases**: URL loading, advanced shapes, text formatting

---

## Running Tests

### Unit Tests (Fast)

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_image_loader.py -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Integration Tests (Medium)

```bash
# Run integration tests (require database)
pytest tests/integration/ -v

# Run specific user story test
pytest tests/integration/test_annotation_workflow.py -v
```

### Contract Tests (API Validation)

```bash
# Validate API against OpenAPI spec
pytest tests/contract/ -v

# Will check:
# - All endpoints defined in spec are implemented
# - Request/response schemas match
# - Status codes correct
```

### E2E Tests (Slow, Browser Required)

```bash
# Install Playwright browsers (first time)
playwright install

# Run E2E tests
pytest tests/e2e/ -v --headed  # Show browser
pytest tests/e2e/ -v           # Headless

# Run specific E2E scenario
pytest tests/e2e/test_editor_e2e.py::test_full_annotation_flow -v
```

### Frontend Tests (JavaScript)

```bash
# If Jest is set up
npm test

# Watch mode for development
npm test -- --watch
```

---

## Manual Testing

### Test Annotation Workflow (User Story 1)

```bash
# 1. Start server
uvicorn src.main:app --reload

# 2. Create test image
convert -size 800x600 xc:white test.png  # ImageMagick

# 3. Open in editor
imgcat test.png

# 4. In browser:
#    - Click pen tool
#    - Draw circle
#    - Click arrow tool
#    - Draw arrow
#    - Click text tool
#    - Add text "Bug here"
#    - Click "Copy to Clipboard"
#    - Paste in Slack/Discord

# 5. Verify copied image has annotations
```

### Test Clipboard Workflow (User Story 2)

```bash
# 1. Take screenshot (Cmd+Shift+4 on macOS)
# 2. Run: pbpaste | imgcat
# 3. Verify editor opens with screenshot
# 4. Add annotations
# 5. Click "Copy to Clipboard"
# 6. Paste in external app
```

### Test Undo/Redo

```bash
# 1. Open image: imgcat test.png
# 2. Draw 5 shapes
# 3. Click Undo 3 times → should remove last 3 shapes
# 4. Click Redo 2 times → should restore 2 shapes
# 5. Draw new shape → redo stack should clear
# 6. Try Cmd+Z / Cmd+Shift+Z shortcuts
```

---

## Debugging Tips

### Backend Debugging

```python
# Add logging to services
import logging
logger = logging.getLogger(__name__)

class ImageLoaderService:
    async def load_from_file(self, path: str, terminal_id: str):
        logger.info(f"Loading image from {path} for terminal {terminal_id}")
        # ...
```

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uvicorn src.main:app --reload
```

### Frontend Debugging

```javascript
// In static/js/image-editor.js
class ImageEditor {
    drawAnnotation(tool, config) {
        console.log("Drawing with tool:", tool, "config:", config);
        // Enable Fabric.js debug mode
        fabric.Object.prototype.set({
            transparentCorners: false,
            borderColor: 'blue',
            cornerColor: 'blue'
        });
    }
}
```

```bash
# Open browser DevTools
# Network tab → check API calls
# Console tab → check JavaScript errors
# Application tab → check session storage
```

### Database Debugging

```bash
# Inspect database
sqlite3 jterm.db

# Check sessions
SELECT * FROM image_sessions ORDER BY created_at DESC LIMIT 5;

# Check annotation layers
SELECT id, session_id, version FROM annotation_layers;

# Check undo history
SELECT session_id, operation_type, position FROM edit_operations ORDER BY timestamp DESC LIMIT 10;
```

---

## Performance Profiling

### Backend Performance

```bash
# Install profiling tools
pip install py-spy

# Profile running server
py-spy record -o profile.svg --pid $(pgrep -f uvicorn)

# Generate flamegraph
open profile.svg
```

### Frontend Performance

```javascript
// In browser DevTools
// Performance tab → Start recording
// Perform operations (draw, undo, filter)
// Stop recording
// Analyze: Should see <50ms per draw operation
```

---

## Common Issues & Solutions

### Issue: "Image too large" error

```python
# Solution: Check file size before loading
if os.path.getsize(path) > 50 * 1024 * 1024:
    raise ValueError("Image exceeds 50MB limit")
```

### Issue: Clipboard permissions denied

```javascript
// Solution: Check permissions and provide fallback
try {
    await navigator.clipboard.write([...]);
} catch (err) {
    if (err.name === 'NotAllowedError') {
        alert('Clipboard permission denied. Please allow clipboard access.');
    }
}
```

### Issue: Canvas performance slow with many objects

```javascript
// Solution: Use Fabric.js object caching
canvas.renderOnAddRemove = false;
// ... add multiple objects ...
canvas.renderAll();
canvas.renderOnAddRemove = true;
```

### Issue: Undo/redo consuming too much memory

```python
# Solution: Compress canvas JSON before storing
import gzip
import json

def store_operation(canvas_json):
    json_str = json.dumps(canvas_json)
    compressed = gzip.compress(json_str.encode())
    # Store compressed data
```

---

## Deployment Checklist

Before merging to main:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] E2E tests pass (at least smoke tests)
- [ ] API contract tests validate against spec
- [ ] Manual testing of all P1 user stories complete
- [ ] Performance benchmarks meet targets
- [ ] No console errors in browser
- [ ] Database migration reviewed and tested
- [ ] Documentation updated (CLAUDE.md)
- [ ] Code reviewed by another developer

---

## Getting Help

**Documentation**:
- [Feature Spec](./spec.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/)
- [Research Decisions](./research.md)

**Key Libraries**:
- [Fabric.js Docs](http://fabricjs.com/docs/)
- [Pillow Docs](https://pillow.readthedocs.io/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

**Testing Resources**:
- [pytest Documentation](https://docs.pytest.org/)
- [Playwright Python](https://playwright.dev/python/)

**Questions**:
- Check existing tests for examples
- Review research.md for technology decisions
- Consult data-model.md for database schema
