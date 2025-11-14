# Implementation Plan: imgcat Image Editor

**Branch**: `004-imgcat-editor` | **Date**: 2025-11-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-imgcat-editor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Extend the existing imgcat command with comprehensive image editing capabilities. Users can annotate, crop, resize, apply filters, and edit images from file paths, clipboard, URLs, or session history. The feature provides a web-based canvas editor integrated with jterm's terminal interface, supporting clipboard operations, undo/redo, and multiple drawing tools. Core workflows (annotation, clipboard, crop/resize) are P1, with filters and advanced features as P2/P3 enhancements.

## Technical Context

**Language/Version**: Python 3.11+ (backend), JavaScript ES2022 (frontend)
**Primary Dependencies**:
  - Backend: FastAPI, Pillow (image processing), aiohttp (URL loading), aiosqlite
  - Frontend: HTML5 Canvas API, Fabric.js (canvas object management), HTMX
**Storage**: SQLite (session history persistence), File system (image files, temp storage)
**Testing**: pytest (backend unit/integration), Jest (frontend unit), Playwright (E2E)
**Target Platform**: Web-based UI served via FastAPI, macOS/Linux/Windows terminal environments
**Project Type**: Web (existing single FastAPI application)
**Performance Goals**:
  - Image load <1s (5MB files)
  - Canvas operations <50ms latency
  - Undo/redo <100ms
  - Filter preview <200ms
**Constraints**:
  - Maximum image size 50MB (jterm media limit)
  - Canvas dimensions limited to 32,767px per side (browser limitation)
  - Clipboard operations require browser permissions
**Scale/Scope**:
  - Support 100+ annotation elements per image
  - Session history limited to 20 images
  - Undo/redo stack depth: 50 operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution file is empty/template-only. No project-specific principles defined yet.

**Default Compliance Assessment**:
- ✅ **Simplicity**: Feature extends existing imgcat command rather than creating new tools
- ✅ **Test-First**: TDD workflow will be followed (unit tests → integration tests → E2E tests)
- ✅ **Existing Architecture**: Leverages jterm's FastAPI + HTMX + xterm.js architecture
- ✅ **No Over-Engineering**: Uses proven libraries (Pillow, Fabric.js) rather than building from scratch
- ⚠️ **Clipboard Integration**: Platform-specific clipboard utilities required (pbpaste/xclip) - necessary for user workflows

**Note**: Project constitution appears to be uninitialized. Proceeding with standard best practices.

## Project Structure

### Documentation (this feature)

```text
specs/004-imgcat-editor/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-endpoints.yaml      # OpenAPI spec for image editor endpoints
│   └── websocket-messages.yaml # WebSocket message contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Existing jterm structure (single FastAPI application)
src/
├── models/
│   └── image_editor.py         # NEW: ImageSession, AnnotationLayer, EditOperation
├── services/
│   ├── image_editor_service.py # NEW: Core editing logic
│   ├── image_loader_service.py # NEW: File/URL/clipboard loading
│   └── media_service.py        # EXISTING: Extended for editor integration
├── api/
│   └── image_editor.py         # NEW: REST endpoints for editor operations
├── websockets/
│   └── image_editor.py         # NEW: Real-time canvas updates
├── middleware/
│   └── [existing auth/logging]
└── database/
    └── [existing SQLite setup]

templates/
├── components/
│   ├── image_editor.html       # NEW: Main editor UI component
│   ├── toolbar.html            # NEW: Drawing tools toolbar
│   └── filter_panel.html       # NEW: Filter/adjustment controls
└── [existing base/terminal templates]

static/
├── js/
│   ├── image-editor.js         # NEW: Canvas management with Fabric.js
│   ├── drawing-tools.js        # NEW: Tool implementations (pen, arrow, text, shapes)
│   ├── filter-engine.js        # NEW: Image filter/adjustment logic
│   └── clipboard-handler.js   # NEW: Clipboard copy/paste operations
├── css/
│   └── image-editor.css        # NEW: Editor UI styling
└── assets/
    └── [existing assets]

tests/
├── contract/
│   └── test_image_editor_api.py     # NEW: API contract tests
├── integration/
│   ├── test_annotation_workflow.py  # NEW: User Story 1 tests
│   ├── test_clipboard_workflow.py   # NEW: User Story 2 tests
│   └── test_crop_resize.py          # NEW: User Story 3 tests
├── unit/
│   ├── test_image_editor_service.py # NEW: Service layer tests
│   └── test_image_loader.py         # NEW: Loader tests
└── e2e/
    └── test_editor_e2e.py            # NEW: Playwright browser tests
```

**Structure Decision**: Single project architecture maintained. All image editor functionality integrated into existing jterm FastAPI application following established patterns (models, services, api, websockets). Frontend uses existing HTMX approach with Fabric.js for canvas management.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations identified. Feature follows existing jterm architecture patterns and complexity level.

## Phase 0: Research & Technology Decisions

### Research Tasks

The following areas require research to resolve design decisions:

1. **Canvas Library Selection** (NEEDS CLARIFICATION)
   - **Question**: Should we use Fabric.js, Konva.js, or raw Canvas API for annotation management?
   - **Context**: Need object selection, manipulation, serialization for undo/redo
   - **Research needed**: Performance comparison, feature completeness, bundle size

2. **Image Processing Strategy** (NEEDS CLARIFICATION)
   - **Question**: Should filters/adjustments be applied client-side (Canvas) or server-side (Pillow)?
   - **Context**: Balance between performance and server load
   - **Research needed**: Canvas filter API capabilities, Pillow performance benchmarks

3. **Clipboard API Approach** (NEEDS CLARIFICATION)
   - **Question**: How to handle clipboard operations across different platforms?
   - **Context**: Browser Clipboard API requires HTTPS + permissions; terminal clipboard (pbpaste) is platform-specific
   - **Research needed**: Browser Clipboard API compatibility, fallback strategies

4. **Session History Persistence** (NEEDS CLARIFICATION)
   - **Question**: Should session history be persisted in SQLite or kept in-memory?
   - **Context**: Balance between session continuity and storage overhead
   - **Research needed**: Performance impact, cleanup strategies

5. **Undo/Redo Implementation Pattern** (NEEDS CLARIFICATION)
   - **Question**: Command pattern vs. state snapshots for undo/redo?
   - **Context**: Need <100ms undo/redo with 50-operation depth
   - **Research needed**: Memory usage, performance characteristics

See `research.md` for detailed findings and decisions.

## Phase 1: Design Artifacts

### Data Models

See `data-model.md` for complete entity definitions, field specifications, and relationships.

**Key Entities**:
- ImageSession: Tracks loaded image and editing state
- AnnotationLayer: Manages canvas annotations (drawings, text, shapes)
- EditOperation: Undo/redo history entries
- SessionHistory: Recently viewed images for quick access

### API Contracts

See `contracts/` directory for complete OpenAPI and WebSocket specifications.

**Key Endpoints**:
- `POST /api/image-editor/load` - Load image from file/URL/clipboard
- `POST /api/image-editor/save` - Save edited image
- `GET /api/image-editor/history` - Get session history
- `POST /api/image-editor/process` - Apply server-side filters/operations
- WebSocket `/ws/image-editor/{session_id}` - Real-time canvas sync

### Developer Quickstart

See `quickstart.md` for setup instructions, development workflow, and testing guidelines.

## Phase 2: Task Generation

Task generation is handled by the `/speckit.tasks` command (separate from this planning phase).

After this plan is complete, run `/speckit.tasks` to generate `tasks.md` with:
- Dependency-ordered implementation tasks
- Test-first workflow (tests before implementation)
- Phased delivery aligned with user story priorities (P1 → P2 → P3)

## Next Steps

1. ✅ Complete this plan.md
2. → Run Phase 0: Generate research.md (resolves all NEEDS CLARIFICATION items)
3. → Run Phase 1: Generate data-model.md, contracts/, quickstart.md
4. → Update agent context with new technologies
5. → User runs `/speckit.tasks` to generate actionable task list
