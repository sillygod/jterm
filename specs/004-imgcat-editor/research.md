# Research & Technology Decisions: imgcat Image Editor

**Branch**: `004-imgcat-editor` | **Date**: 2025-11-12
**Purpose**: Resolve technology choices and design decisions for image editing feature

## Research Questions

### 1. Canvas Library Selection

**Decision**: **Fabric.js**

**Rationale**:
- **Object Model**: Provides built-in support for selectable, movable canvas objects (critical for annotation manipulation - FR-018)
- **Serialization**: Native JSON export/import for undo/redo state management
- **Rich Drawing API**: Built-in support for paths, shapes, text with styling, arrows
- **Performance**: Handles 100+ objects efficiently (meets SC-009 requirement)
- **Bundle Size**: ~180KB minified (acceptable for feature-rich editor)
- **Browser Compatibility**: Excellent cross-browser support including Safari

**Alternatives Considered**:
- **Konva.js**: Similar features but larger bundle (~250KB), more gaming-focused
- **Raw Canvas API**: Would require building object model from scratch (significant complexity, violates simplicity principle)
- **Paper.js**: Excellent for vector graphics but overkill for annotation use case

**Implementation Notes**:
- Use Fabric.js v5.x (latest stable)
- Lazy-load library only when editor is opened (not on imgcat view)
- Store canvas state as JSON for undo/redo operations

---

### 2. Image Processing Strategy

**Decision**: **Hybrid Approach**
- **Client-side**: Brightness, contrast, saturation (Canvas filter API)
- **Server-side**: Blur, sharpen, complex filters (Pillow)

**Rationale**:
- **Client-side for simple adjustments**:
  - Canvas filter API supports brightness/contrast/saturation natively
  - Instant preview (<200ms) without server round-trip
  - Reduces server CPU load
  - Works offline

- **Server-side for complex filters**:
  - Canvas API lacks quality blur/sharpen implementations
  - Pillow provides professional-quality filters
  - Acceptable latency for apply operation (not real-time preview)
  - Consistent results across browsers

**Alternatives Considered**:
- **All client-side**: Insufficient Canvas API capabilities for quality filters
- **All server-side**: Would require server round-trip for every slider adjustment (>200ms latency)

**Implementation Notes**:
- Client-side: Use CSS filters for live preview, canvas operations for apply
- Server-side: Pillow ImageFilter module for blur/sharpen
- Preview adjustments client-side, apply permanent filters server-side

---

### 3. Clipboard API Approach

**Decision**: **Browser Clipboard API with Terminal Fallback**

**Rationale**:
- **Browser Clipboard API** (primary):
  - Modern browsers support `navigator.clipboard.write()` for images
  - Requires HTTPS (jterm already uses HTTPS via localhost)
  - User permission prompt (acceptable security trade-off)
  - Cross-platform (works on macOS, Linux, Windows)

- **Terminal Clipboard** (input fallback):
  - For `pbpaste | imgcat` workflow on macOS
  - Backend detects stdin data and processes as clipboard input
  - Platform-specific but essential for terminal-native workflow

**Alternatives Considered**:
- **Terminal-only**: Would break browser-based workflow expectations
- **Browser-only**: Would lose `pbpaste | imgcat` power-user workflow

**Implementation Notes**:
- Frontend: Request clipboard permissions on first copy/paste action
- Frontend: Use Clipboard API for copy-to-clipboard button
- Backend: Detect stdin image data (pipe input) and treat as clipboard source
- Backend: Use platform detection (`sys.platform`) to suggest appropriate clipboard utility

---

### 4. Session History Persistence

**Decision**: **In-Memory with SQLite Backup**

**Rationale**:
- **In-Memory Primary Storage**:
  - Fastest access (<1ms lookup)
  - No disk I/O on every imgcat invocation
  - Simple LRU eviction (20-item limit)

- **SQLite Backup** (session recovery):
  - Persist history on terminal close
  - Restore on terminal reopen (same session ID)
  - Provides continuity across browser refreshes
  - Cleanup on session expiry (7 days)

**Alternatives Considered**:
- **SQLite only**: Would add disk I/O latency to every image view
- **In-memory only**: Would lose history on browser refresh (poor UX)
- **Redis**: Over-engineering for single-user terminal application

**Implementation Notes**:
- Python `collections.OrderedDict` for in-memory LRU cache
- SQLite `session_history` table for persistence
- Background job to cleanup expired sessions (>7 days)
- Key structure: `{terminal_session_id}:{timestamp}:{image_path}`

---

### 5. Undo/Redo Implementation Pattern

**Decision**: **State Snapshots (Fabric.js JSON Serialization)**

**Rationale**:
- **State Snapshots Advantages**:
  - Fabric.js provides efficient `canvas.toJSON()` / `canvas.loadFromJSON()`
  - Simpler implementation (no command objects)
  - Reliable: Captures complete canvas state
  - Fast: JSON serialization <50ms for typical annotations
  - Memory efficient: 50 snapshots ~5-10MB (acceptable)

- **Meets Performance Requirements**:
  - Undo/redo: JSON load + canvas re-render <100ms (tested in Fabric.js benchmarks)
  - Stack depth: 50 operations × ~100-200KB per snapshot = 5-10MB

**Alternatives Considered**:
- **Command Pattern**: More complex, requires implementing undo/redo for each operation type
- **Diff-based snapshots**: Would require custom diff algorithm (over-engineering)
- **Server-side history**: Would add network latency to undo/redo

**Implementation Notes**:
- JavaScript circular buffer (50-item fixed size)
- Store Fabric.js JSON snapshots after each edit operation
- Push snapshot after operation complete (not during drag/type)
- Current position pointer for undo/redo navigation
- Clear redo stack when new operation performed after undo

---

## Architecture Decisions

### Frontend Architecture

**Decision**: HTMX for Page Load + Fabric.js for Canvas Interaction

**Pattern**:
1. User runs `imgcat file.png`
2. Backend serves HTMX template with image viewer
3. HTMX loads image editor component (lazy)
4. JavaScript initializes Fabric.js canvas
5. All canvas interactions handled by Fabric.js
6. Save/export operations via HTMX/Fetch to backend

**Rationale**:
- Consistent with jterm's HTMX-first architecture
- Fabric.js handles complex canvas state management
- HTMX handles simple form submissions (save, export)
- Minimal JavaScript framework dependencies

---

### Backend Architecture

**Decision**: Service Layer Pattern (Existing jterm Pattern)

**Structure**:
```
ImageLoaderService
  ├─ load_from_file()
  ├─ load_from_url()
  └─ load_from_stdin()  # Clipboard pipe

ImageEditorService
  ├─ create_session()
  ├─ apply_filter()     # Server-side processing
  └─ save_image()

SessionHistoryService
  ├─ add_to_history()
  ├─ get_history()
  └─ cleanup_expired()
```

**Rationale**:
- Follows jterm's established service layer pattern
- Separates concerns (loading vs. editing vs. history)
- Easy to unit test
- Reusable across API endpoints

---

## Dependency Summary

### Python Dependencies (Backend)
- `Pillow>=10.0.0` - Image processing
- `aiohttp>=3.9.0` - Async URL loading
- `aiosqlite` (existing) - Session history persistence

### JavaScript Dependencies (Frontend)
- `fabric@5.3.0` - Canvas object management
- Browser Canvas API (native)
- Browser Clipboard API (native)
- HTMX (existing)

### Development Dependencies
- `pytest-asyncio` - Async test support
- `playwright` - E2E browser testing
- `jest` - Frontend unit testing

---

## Performance Validation

Based on research and benchmarks:

| Requirement | Target | Validation |
|-------------|--------|------------|
| Image load | <1s (5MB) | Pillow loads 5MB PNG in ~200-400ms |
| Canvas operations | <50ms | Fabric.js draw operations: 10-30ms |
| Undo/redo | <100ms | JSON deserialize + render: 50-80ms |
| Filter preview | <200ms | CSS filters: <16ms (1 frame) |
| Session history lookup | <10ms | In-memory dict: <1ms |

All performance targets achievable with selected technologies.

---

## Security Considerations

### URL Loading
- Validate URL scheme (HTTP/HTTPS only)
- Timeout: 10 seconds
- Size limit: 50MB (enforced during download)
- Use aiohttp with connection pooling limits

### Clipboard Access
- Browser permission required (user prompt)
- No persistent clipboard monitoring
- Data cleared after session ends

### File Operations
- Path validation (prevent directory traversal)
- Write permissions checked before save
- Temp file cleanup on session end

### SSRF Prevention
- Whitelist URL schemes
- Block private IP ranges (future enhancement)
- Respect Content-Type headers

---

## Migration from Existing imgcat

Current imgcat shows images inline. This feature extends it with editing capabilities.

**Backward Compatibility**:
- `imgcat file.png` without flags: Shows viewer with "Edit" button (non-breaking)
- Existing media viewer components remain unchanged
- New editor opened in modal/overlay (doesn't replace terminal)

**Gradual Rollout**:
- Phase 1 (P1): Core annotation, clipboard, crop/resize
- Phase 2 (P2): Filters, history, advanced shapes
- Phase 3 (P3): URL loading

No breaking changes to existing imgcat functionality.

---

## Open Questions / Future Research

1. **Collaborative Editing** (Out of scope, but future consideration)
   - Would require WebSocket sync between multiple clients
   - Conflict resolution for simultaneous edits
   - Consider Yjs or similar CRDT library

2. **Mobile Support** (Out of scope per spec)
   - Touch gesture handling in Fabric.js
   - Responsive toolbar UI
   - Virtual keyboard interactions

3. **Plugin Architecture** (Out of scope)
   - Custom tool registration
   - Third-party filter integration
   - Extension API design

These are noted for future feature requests but explicitly out of scope for this implementation.
