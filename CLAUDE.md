# jterm Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-26

## Project Overview
Web-based terminal emulator with multimedia support, animations, AI assistance, and session recording capabilities. Single FastAPI application serving HTMX templates with SQLite storage.

## Active Technologies
- **Backend**: FastAPI, Python 3.11+, SQLite, WebSockets, Python PTY module
- **Frontend**: HTMX, xterm.js, Hyperscript, JavaScript ES2022
- **Storage**: SQLite database + file system for media assets
- **Testing**: pytest (backend), Jest (frontend), Playwright (E2E)
- **Features**: Terminal emulation, media viewing, AI assistant, session recording, themes, extensions
- Python 3.11+ (backend), JavaScript ES2022 (frontend) (002-enhance-and-implement)
- SQLite (aiosqlite) + file system for media caching (002-enhance-and-implement)
- Python 3.11+ (backend), JavaScript ES2022 (frontend) + FastAPI, xterm.js, HTMX, WebSockets, Python PTY module (003-cat-commands)
- SQLite database (existing) + browser localStorage (history/queries) + file system (exports) (003-cat-commands)
- SQLite (session history persistence), File system (image files, temp storage) (004-imgcat-editor)

## Project Structure
```
src/
├── models/          # SQLite data models (Terminal Session, Recording, Media, etc.)
├── services/        # Core business logic (PTY, Media, AI, Recording services)
├── api/            # FastAPI REST endpoints
├── websockets/     # WebSocket handlers for real-time communication
├── middleware/     # Auth, logging, security middleware
└── database/       # SQLite connection and migrations

templates/
├── base.html       # Base HTMX template
├── terminal.html   # Main terminal interface
└── components/     # HTMX components (media viewer, AI sidebar, etc.)

static/
├── js/            # Frontend JavaScript and Hyperscript
├── css/           # Styling
└── assets/        # Static assets

tests/
├── contract/      # API contract tests
├── integration/   # User story integration tests
├── unit/          # Unit tests for services
├── performance/   # Performance benchmarks
└── e2e/          # End-to-end browser tests
```

## Key Features
1. **Terminal Emulation**: xterm.js with WebSocket PTY communication
2. **Media Support**: Inline images (<1s load), videos (50MB max), HTML preview with sandboxing
3. **Ebook Viewer** (`bookcat` command): PDF and EPUB rendering with foliate-js, password-protected PDF support, up to 50MB files
4. **Image Editor** (`imgcat` with edit mode): Web-based canvas editor with annotation tools, filters, crop/resize, clipboard support, undo/redo (50 operations), session history (20 images)
5. **AI Assistant**: Voice input/output, context-aware suggestions (2s simple, 5s complex responses)

https://github.com/KoljaB/RealtimeSTT (options)
ps aux | grep "jterm/venv/bin/python3" | awk '{print $2}' | xargs kill -9 (clean some orphan processes)


6. **Session Recording**: Record/replay/export with 30-day retention, <5% performance impact, responsive width scaling (80-200 columns)
7. **Performance Monitoring**: Real-time CPU/memory metrics, configurable refresh intervals, 24-hour retention
8. **Customization**: Themes, extensions, VS Code theme import
9. **Security**: HTML sandboxing, file validation, secure API communications, path traversal prevention, SSRF protection

## Development Commands
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Development
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Testing
pytest tests/                    # Backend tests
npm test                        # Frontend tests
playwright test                 # E2E tests

# Linting
black src/ tests/
flake8 src/ tests/
```

## Code Style
- **Python**: Black formatting, flake8 linting, type hints required
- **JavaScript**: ES2022 features, async/await patterns
- **HTMX**: Template-based approach, minimal JavaScript
- **Testing**: TDD approach - tests written before implementation
- **Architecture**: Single responsibility principle, service layer pattern

## Performance Requirements
- **Image loading**: <1 second
- **AI responses**: <2s simple, <5s complex
- **Ebook rendering**: PDF (<3s for 10MB), EPUB (<2s for 5MB)
- **Page navigation**: <500ms
- **Recording playback resize**: <200ms
- **CPU usage**:
  - Idle: <5% (achieved: 0.08%, 99.9% reduction from 78.6% baseline)
  - Active terminal: <15%
  - Recording playback: <25%
- **Session recording impact**: <5% performance degradation
- **Video file limit**: 50MB maximum
- **Ebook file limit**: 50MB maximum

## Recent Changes
- **004-imgcat-editor** (2025-11-18): ✅ COMPLETE
  - Added comprehensive image editor with Fabric.js canvas and Pillow image processing
  - **Drawing Tools**: Pen, arrow, text, rectangles, circles, lines with customizable colors and stroke widths
  - **Image Operations**: Crop, resize (with aspect ratio lock), blur, sharpen, brightness/contrast/saturation adjustments
  - **Clipboard Integration**: Load images from system clipboard (macOS/Windows), copy edited images to clipboard
  - **Session History**: Quick re-edit of recently viewed images (`imgcat --history`, `imgcat -e N`)
  - **URL Loading**: Load and edit images directly from HTTP/HTTPS URLs with SSRF protection
  - **Undo/Redo**: 50-operation circular buffer with canvas state snapshots
  - **Security**: Path validation, SQL injection prevention (UUID validation), directory traversal blocking
  - **Performance**: Image downsampling for large files (>4096px), canvas JSON gzip compression, cleanup jobs for expired sessions
  - **Storage**: SQLite for session management, annotation layers, edit history, session history (7-day retention)
  - Commands: `imgcat file.png`, `imgcat --clipboard`, `imgcat URL`, `imgcat --history`, `imgcat -e 2`
  - Libraries: Pillow (backend image processing), Fabric.js 5.3.0 (frontend canvas), aiohttp (URL loading)
- 003-cat-commands: Added Python 3.11+ (backend), JavaScript ES2022 (frontend) + FastAPI, xterm.js, HTMX, WebSockets, Python PTY module
  - Added ebook viewer (`bookcat` command) with PDF/EPUB support via foliate-js
  - Implemented recording playback responsive width scaling (80-200 columns)
  - **CPU optimization**: Reduced idle CPU from 78.6% to 0.08% (99.9% reduction!)
    - WebSocket ping interval: 30s → 60s
    - Terminal output debouncing: 100ms batch window
    - **Critical fix**: PTY output timeout 0.1s → 1.0s (eliminated primary CPU consumer)
    - Lazy-load xterm.js addons (deferred loading)
  - Added performance monitoring with real-time metrics display
  - Libraries: PyPDF2 (PDF), ebooklib (EPUB), psutil (performance), foliate-js (frontend)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
