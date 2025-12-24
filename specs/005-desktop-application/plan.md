# Implementation Plan: Desktop Application Conversion

**Branch**: `005-desktop-application` | **Date**: 2025-12-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-desktop-application/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Convert jterm web terminal to a native desktop application using Tauri (Rust-based desktop framework) with PyInstaller (Python bundler) to package the existing FastAPI backend. The desktop app will maintain complete feature parity with the web version, including terminal emulation, media viewing, image editing, session recording, AI assistant, performance monitoring, and cat commands. Tauri provides lightweight native windows (using system WebView) while PyInstaller bundles the Python backend into a standalone executable, enabling seamless integration of the web-based UI with native OS features.

## Technical Context

**Language/Version**:
- **Frontend**: Rust 1.85+ (Tauri framework with edition2024 support), JavaScript ES2022 (existing web UI)
- **Backend**: Python 3.11+ (existing FastAPI services)
- **Build Tools**: Node.js 18+ (for frontend build), Cargo (Rust package manager)

**Primary Dependencies**:
- **Desktop Framework**: Tauri 2.9+ (native window, system integration, IPC)
- **Backend Bundler**: PyInstaller 6.0+ (Python executable packaging)
- **Existing Stack**: FastAPI, xterm.js, Fabric.js, foliate-js, Pillow, SQLAlchemy, aiosqlite
- **Native APIs**: Platform-specific PTY (posix_openpt on macOS/Linux, ConPTY on Windows), clipboard APIs

**Storage**:
- SQLite database in platform-standard locations (macOS: ~/Library/Application Support/jterm, Windows: %APPDATA%/jterm, Linux: ~/.local/share/jterm)
- File system for media assets, recordings, temporary files

**Testing**:
- **Backend**: pytest (existing test suite reused)
- **Frontend**: Jest (existing JavaScript tests)
- **Integration**: Tauri's test framework for native integration
- **E2E**: Playwright or WebDriver for desktop app E2E tests

**Target Platform**:
- macOS 10.15+ (Catalina and later)
- Windows 10+ (x64)
- Linux (Ubuntu 20.04+, Fedora 35+, with modern kernel and GLIBC)

**Project Type**: Desktop application (hybrid: Tauri native wrapper + existing web UI + bundled Python backend)

**Performance Goals**:
- Launch time: <3 seconds cold start
- CPU usage: <5% idle, <15% active terminal, <25% recording playback (matching web version)
- Memory: <200MB base, <500MB with 10 active tabs
- Image load: <1 second for 10MB files
- AI response: <2s simple queries, <5s complex queries

**Constraints**:
- Bundle size: 150-300MB installed (including Python runtime, Tauri framework, dependencies)
- Offline-capable: Full functionality except AI assistant (requires network for API calls)
- Cross-platform: Single codebase for macOS/Windows/Linux with platform-specific adaptations
- Feature parity: All web version features must work identically in desktop version
- Backward compatibility: Seamless migration of existing SQLite database schema

**Scale/Scope**:
- Codebase: ~30,000 lines Python (existing, 100% reused) + ~3,000 lines Rust (Tauri integration) + ~500 lines JS (desktop-specific)
- Features: 10 major feature areas (terminal, media, image editor, recording, AI, performance, themes, extensions, cat commands)
- Platform-specific code: ~10% (clipboard, file dialogs, menu bars, system integration)
- Reused code: ~90% (entire FastAPI backend including PTY, all JavaScript UI components, all WebSocket handlers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASSED (No constitution defined - using jterm project conventions)

**Note**: The constitution file is currently a template with placeholders. Based on existing jterm codebase patterns observed in CLAUDE.md, the project follows these conventions:

1. **Testing Standards**: TDD approach with comprehensive test coverage (unit, integration, contract, performance, E2E)
2. **Code Style**: Black formatting (Python), flake8 linting, type hints required, ES2022 features (JavaScript)
3. **Architecture**: Service layer pattern, single responsibility principle, async/await throughout
4. **Performance Requirements**: Specific targets for CPU, memory, response times (documented in spec)
5. **Security**: Input validation, sandboxing, SSRF protection, SQL injection prevention

**Alignment Check**:
- ✅ Reusing existing backend (preserves tested code, minimizes regression risk)
- ✅ Maintaining test suite (pytest for backend, Jest for frontend)
- ✅ Following service architecture (Tauri commands map to existing services)
- ✅ Performance targets match web version (<5% CPU idle, <1s image load, etc.)
- ✅ Security requirements carried forward (file validation, sandboxing, SSRF protection)

**No violations** - This feature extends the existing architecture with a native wrapper while preserving all established patterns.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Existing Web Application Structure (PRESERVED)
src/                              # Python backend (28,124 lines - REUSED)
├── main.py                       # FastAPI entry point (MODIFIED for desktop)
├── config.py                     # Environment config (MODIFIED for desktop paths)
├── models/                       # SQLAlchemy ORM (15 files - REUSED)
├── services/                     # Business logic (18 services - REUSED)
├── api/                          # REST endpoints (14 routers - REUSED)
├── websockets/                   # WebSocket handlers (3 handlers - REUSED)
├── middleware/                   # Auth, logging, security (REUSED)
├── database/                     # Connection & migrations (REUSED)
└── utils/                        # Validators, logging (REUSED)

static/                           # Frontend assets (REUSED)
├── js/                           # 22 JS modules (REUSED)
├── css/                          # Styling + themes (REUSED)
└── assets/                       # Images, icons (REUSED)

templates/                        # Jinja2 HTML templates (REUSED)
├── base.html                     # Main layout (MODIFIED for desktop)
├── terminal.html                 # Terminal UI (REUSED)
└── components/                   # 18 components (REUSED)

tests/                            # Test suite (REUSED + EXTENDED)
├── unit/                         # Service tests (REUSED)
├── integration/                  # User story tests (EXTENDED)
├── contract/                     # API contract tests (REUSED)
├── performance/                  # Benchmarks (EXTENDED)
├── security/                     # Security tests (REUSED)
└── e2e/                          # E2E tests (NEW - desktop-specific)

# NEW: Tauri Desktop Application Structure
src-tauri/                        # Tauri Rust code (NEW - ~3,000 lines)
├── Cargo.toml                    # Rust dependencies
├── tauri.conf.json               # Tauri configuration
├── build.rs                      # Build script
├── icons/                        # App icons (macOS/Windows/Linux)
└── src/
    ├── main.rs                   # Tauri app entry point
    ├── commands/                 # Tauri commands (native-only features)
    │   ├── mod.rs
    │   ├── clipboard.rs          # Clipboard integration (native OS API)
    │   ├── file_dialogs.rs       # Native file dialogs (OS file picker)
    │   ├── menu.rs               # Menu bar operations (OS menu bar)
    │   └── system.rs             # System integration (window title, notifications, etc.)
    ├── python/                   # Python backend integration
    │   ├── mod.rs
    │   ├── bundler.rs            # PyInstaller bundling logic
    │   ├── launcher.rs           # Python process management
    │   └── health.rs             # Backend health checks
    └── utils/                    # Utilities
        ├── mod.rs
        ├── db_path.rs            # Platform-specific DB paths
        └── logging.rs            # Desktop logging

# NEW: Desktop-specific frontend code
src-tauri/ui/                     # Desktop UI adaptations (NEW - ~500 lines)
├── index.html                    # Entry point (loads from bundled Python server)
├── desktop.js                    # Desktop-specific JS (Tauri API calls for native features)
└── desktop.css                   # Desktop-specific styles (window chrome, etc.)

# NEW: Build and distribution
scripts/                          # Build scripts (NEW)
├── build-python.sh               # PyInstaller build script
├── build-tauri.sh                # Tauri build script
├── package-macos.sh              # macOS DMG creation
├── package-windows.sh            # Windows MSI creation
└── package-linux.sh              # Linux AppImage/DEB/RPM creation

# Existing (PRESERVED)
migrations/                       # Alembic migrations (REUSED)
requirements.txt                  # Python dependencies (REUSED)
package.json                      # Node.js dependencies (MODIFIED - add Tauri)
```

**Structure Decision**: Hybrid desktop application structure

This design preserves the existing web application codebase (src/, static/, templates/, tests/) and adds a new Tauri layer (src-tauri/) that wraps it. The Python backend is bundled with PyInstaller and launched as a subprocess by the Tauri Rust application. The existing web UI is served from the bundled Python server and rendered in Tauri's WebView.

**Key Integration Points**:
1. **Tauri Main** → launches bundled Python backend → connects to localhost API
2. **Tauri Commands** → expose native-only operations (clipboard, file dialogs, menus) → called from JavaScript
3. **Python Backend** → serves existing web UI + API → handles ALL business logic including PTY
4. **Frontend** → loads in Tauri WebView → uses WebSocket for terminal I/O (unchanged from web) → calls Tauri APIs only for native features

**Benefits**:
- **Code Reuse**: 90% of codebase unchanged (entire backend including PTY + UI + WebSocket handlers)
- **Maintainability**: Single source of truth for business logic (no PTY duplication)
- **Testing**: Existing test suite 100% valid (PTY tests unchanged)
- **Platform Support**: Tauri handles OS-specific native features, Python handles PTY
- **Bundle Size**: Smaller than Electron (Tauri uses system WebView)
- **Simpler Architecture**: No Rust-Python IPC for terminal operations

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - No complexity tracking required. The implementation adds a Tauri wrapper layer while preserving the existing architecture, resulting in minimal additional complexity that is justified by cross-platform desktop requirements.
