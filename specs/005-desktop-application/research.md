# Research: Desktop Application Conversion

**Feature**: 005-desktop-application
**Date**: 2025-12-13
**Status**: Complete

## Overview

This document captures research findings and technical decisions for converting the jterm web terminal to a native desktop application using Tauri with PyInstaller.

---

## 1. Desktop Framework Selection

### Decision: Tauri 2.9+

**Rationale**:
- **Lightweight**: Uses system WebView instead of bundling Chromium (unlike Electron)
- **Performance**: Rust core provides excellent performance and low memory footprint
- **Security**: Strong security model with granular permissions and IPC sandboxing
- **Bundle Size**: 50-100MB smaller than equivalent Electron app
- **Python Integration**: Well-documented patterns for integrating external processes
- **Cross-Platform**: Single codebase for macOS, Windows, Linux with platform-specific APIs
- **Active Development**: Strong community, frequent updates, stable 1.x release

**Alternatives Considered**:

| Framework | Why Rejected |
|-----------|--------------|
| **Electron** | Bundle size 3-4x larger (300-500MB vs 150-300MB for Tauri); higher memory usage (~150MB base vs ~50MB for Tauri); includes unnecessary Chromium and Node.js runtimes |
| **PyQt6/PySide6** | Requires complete UI rewrite; cannot reuse existing web UI components (xterm.js, Fabric.js, foliate-js); steeper learning curve; less modern UI capabilities |
| **Tkinter** | Limited UI capabilities; outdated appearance; poor cross-platform consistency; no support for modern web technologies |
| **wxPython** | Cannot reuse web UI; requires significant UI development; smaller community than Qt |
| **NW.js** | Similar to Electron but less mature; smaller community; fewer resources |
| **Neutralinojs** | Less mature than Tauri; smaller community; less robust Python integration patterns |

**Trade-offs Accepted**:
- Adds Rust dependency (manageable: Rust toolchain installed once during development)
- Requires learning Tauri APIs (mitigated: excellent documentation, similar to Electron patterns)
- Smaller ecosystem than Electron (mitigated: Tauri provides all needed features, active plugin development)

---

## 2. Python Backend Bundling

### Decision: PyInstaller 6.0+

**Rationale**:
- **Mature**: Industry-standard Python bundler with 15+ years of development
- **Cross-Platform**: Single bundling approach for macOS, Windows, Linux
- **Compatibility**: Works with FastAPI, SQLAlchemy, aiosqlite, Pillow, and all jterm dependencies
- **One-File Mode**: Can bundle entire Python app into single executable
- **Hidden Imports**: Handles dynamic imports and implicit dependencies
- **Size Optimization**: --strip, --upx, and exclusion options reduce bundle size
- **Hook System**: Extensible hooks for complex dependencies

**Alternatives Considered**:

| Tool | Why Rejected |
|------|--------------|
| **PyOxidizer** | More complex configuration; less mature; steeper learning curve; fewer community resources for FastAPI apps |
| **Nuitka** | Compilation approach slower than bundling; potential compatibility issues with dynamic imports; larger binary size |
| **cx_Freeze** | Less active development; fewer hooks for modern dependencies; more manual configuration required |
| **py2exe** | Windows-only; outdated; not maintained |
| **py2app** | macOS-only; less flexible than PyInstaller |

**Trade-offs Accepted**:
- Larger bundle size (~100-150MB for Python runtime + dependencies) - acceptable for desktop app
- Startup time includes Python initialization (~0.5-1s) - still meets <3s launch target
- Some dynamic imports may require manual hook configuration - mitigated by extensive PyInstaller hook ecosystem

---

## 3. Architecture Pattern

### Decision: Hybrid Desktop Application (Tauri Wrapper + Embedded Python Server)

**Architecture**:
```
Tauri Desktop App
├── Rust Main Process
│   ├── Launches PyInstaller-bundled Python backend as subprocess
│   ├── Waits for Python server to be ready (localhost:random_port)
│   └── Creates WebView pointing to http://localhost:<port>
├── WebView (System Browser Engine)
│   ├── Loads existing web UI from Python server
│   ├── Calls Tauri commands via window.__TAURI__.invoke()
│   └── Communicates with Python backend via HTTP/WebSocket
└── Native Features (Tauri Rust)
    ├── Platform-specific PTY (macOS: posix_openpt, Windows: ConPTY, Linux: pty)
    ├── Clipboard integration (macOS: NSPasteboard, Windows: Clipboard API, Linux: X11)
    ├── File dialogs (native OS dialogs)
    └── Menu bars (platform-specific menus)
```

**Rationale**:
- **Code Reuse**: 80% of codebase unchanged (entire FastAPI backend + web UI)
- **Separation of Concerns**: Tauri handles native features, Python handles business logic
- **Maintainability**: Single source of truth for business logic (Python services)
- **Testability**: Existing test suite remains valid
- **Flexibility**: Can update Python backend without Rust recompilation

**Alternatives Considered**:

| Pattern | Why Rejected |
|---------|--------------|
| **Direct Rust-Python Bindings (PyO3)** | Requires rewriting business logic in Rust; cannot reuse existing FastAPI services; much higher development cost |
| **Python-Only (PyQt/Tkinter)** | Cannot reuse web UI; requires complete UI rewrite; loses xterm.js, Fabric.js, foliate-js |
| **Tauri + Native Python** | Requires user to install Python; version compatibility issues; deployment complexity |

**Trade-offs Accepted**:
- Two processes (Tauri + Python) instead of one - acceptable overhead (~20MB additional memory)
- IPC latency for native features - mitigated by async Tauri commands (<10ms overhead)
- Port management complexity - mitigated by dynamic port allocation and health checks

---

## 4. PTY Integration

### Decision: Reuse Existing Python PTY Service

**Approach**:
- **Python Backend**: Use existing `src/services/pty_service.py` (100% code reuse)
- **WebSocket Communication**: Existing terminal WebSocket handler (`/ws/terminal`)
- **No Tauri Involvement**: PTY operations remain in Python, exactly like web version

**Rationale**:
- **Maximum Code Reuse**: ~90% instead of 80% (entire PTY service reused)
- **Battle-Tested**: Python PTY already works and is optimized (1.0s timeout, 99.9% CPU reduction from 78.6% to 0.08%)
- **No Duplication**: Single PTY implementation to maintain (avoid rewriting in Rust)
- **Proven Performance**: Already achieves <5% CPU idle, <15% active terminal
- **Platform Support**: Python PTY service already handles macOS (posix_openpt), Windows (ConPTY), Linux (pty) differences
- **Simpler Architecture**: Fewer moving parts, existing WebSocket protocol handles everything
- **Easier Maintenance**: PTY updates only need to be made once in Python

**Communication Flow** (unchanged from web version):
```
User types in terminal
  ↓
JavaScript (xterm.js) captures input
  ↓
WebSocket (/ws/terminal) → Python PTY Service
  ↓
Python writes to PTY process (existing ptyprocess library)
  ↓
Python reads PTY output (existing async logic with 1.0s timeout)
  ↓
WebSocket → JavaScript (xterm.js) renders output
```

**Tauri's Role**:
- Launch Python backend as subprocess (PyInstaller bundle)
- Create WebView pointing to `http://localhost:<random_port>`
- **No PTY involvement** - all terminal operations go through Python

**Alternatives Considered**:

| Approach | Why Rejected |
|----------|--------------|
| **Implement PTY in Rust** | Code duplication; maintain two implementations; no performance benefit over optimized Python; higher development cost |
| **Portable PTY (xterm-pty)** | Less mature than existing Python PTY; potential compatibility issues; unnecessary rewrite |

**Benefits**:
- ✅ Reuse 18 Python services (including PTY) - 100% unchanged
- ✅ Reuse 3 WebSocket handlers - 100% unchanged
- ✅ Reuse existing PTY optimizations (1.0s timeout, debouncing, lazy-load addons)
- ✅ If PTY needs updates, change once in Python (desktop inherits automatically)
- ✅ Reduced Rust codebase (~3,000 lines instead of ~5,000 lines)

---

## 5. Clipboard Integration

### Decision: Native Clipboard via Tauri Clipboard Plugin

**Approach**:
- **Tauri Plugin**: `tauri-plugin-clipboard` for text/image clipboard access
- **Platform APIs**: Wraps NSPasteboard (macOS), Clipboard API (Windows), X11/Wayland (Linux)
- **Image Support**: PNG, JPEG encoding/decoding for image clipboard

**Rationale**:
- **Official Plugin**: Maintained by Tauri team, well-tested
- **Cross-Platform**: Single API for all platforms
- **Security**: Respects OS permissions and user consent
- **Format Support**: Handles text, HTML, images, files

**Implementation**:
```rust
// src-tauri/src/commands/clipboard.rs
#[tauri::command]
async fn get_clipboard_image() -> Result<Vec<u8>, String> {
    // Returns PNG-encoded image bytes
}

#[tauri::command]
async fn set_clipboard_image(data: Vec<u8>) -> Result<(), String> {
    // Accepts PNG-encoded image bytes
}
```

**JavaScript Integration**:
```javascript
// static/js/desktop.js
async function loadFromClipboard() {
    const imageBytes = await window.__TAURI__.invoke('get_clipboard_image');
    // Convert to blob and load in editor
}
```

---

## 6. File Dialogs

### Decision: Native File Dialogs via Tauri Dialog Plugin

**Approach**:
- **Tauri Plugin**: `tauri-plugin-dialog` for native OS file dialogs
- **Features**: Open file, save file, select directory, file filters

**Rationale**:
- **Native Look**: Uses OS-native dialogs (NSOpenPanel on macOS, File Explorer on Windows, GTK on Linux)
- **User Familiarity**: Users see familiar file picker from their OS
- **Security**: Sandboxed file access with user consent

**Implementation**:
```rust
#[tauri::command]
async fn select_image_file() -> Result<Option<String>, String> {
    let file_path = dialog::FileDialogBuilder::new()
        .add_filter("Images", &["png", "jpg", "jpeg", "gif", "webp", "bmp"])
        .pick_file()
        .await?;
    Ok(file_path.map(|p| p.to_string_lossy().to_string()))
}
```

---

## 7. Menu Bars

### Decision: Platform-Specific Menu Implementation via Tauri Menu API

**Approach**:
- **macOS**: Application menu with standard macOS items (About, Preferences, Quit)
- **Windows/Linux**: File/Edit/View/Help menus
- **Dynamic Menus**: Update menu items based on application state

**Rationale**:
- **Native Experience**: Follows platform conventions
- **Keyboard Shortcuts**: Platform-specific shortcuts (Cmd on macOS, Ctrl on Windows/Linux)
- **Accessibility**: OS-provided accessibility features

**Menu Structure**:
```rust
// macOS
- jterm (application menu)
  - About jterm
  - Preferences...
  - Quit jterm
- File
  - New Tab (Cmd+N)
  - Close Tab (Cmd+W)
- Edit
  - Copy (Cmd+C)
  - Paste (Cmd+V)
- View
  - Recording Controls
  - Performance Monitor
  - AI Assistant
- Window
  - Minimize
  - Zoom

// Windows/Linux
- File
  - New Tab (Ctrl+N)
  - Close Tab (Ctrl+W)
  - Exit (Alt+F4)
- Edit
  - Copy (Ctrl+C)
  - Paste (Ctrl+V)
- View
  - Recording Controls
  - Performance Monitor
  - AI Assistant
- Help
  - About jterm
```

---

## 8. Database Path Management

### Decision: Platform-Standard Application Data Directories

**Paths**:
- **macOS**: `~/Library/Application Support/jterm/webterminal.db`
- **Windows**: `%APPDATA%\jterm\webterminal.db`
- **Linux**: `~/.local/share/jterm/webterminal.db`

**Rationale**:
- **Platform Conventions**: Follows OS-specific guidelines
- **User Expectations**: Users expect app data in standard locations
- **Backup/Migration**: Users know where to find data
- **Permissions**: Standard paths have correct permissions

**Implementation**:
```rust
use tauri::api::path::app_data_dir;

fn get_database_path(config: &tauri::Config) -> PathBuf {
    let app_data = app_data_dir(config).expect("Failed to get app data directory");
    app_data.join("webterminal.db")
}
```

**Migration Strategy**:
- Check for existing database in current directory (web version location)
- If found, copy to platform-standard location on first launch
- Preserve existing data for users upgrading from web to desktop version

---

## 9. Auto-Update Mechanism

### Decision: Tauri Updater Plugin

**Approach**:
- **Tauri Plugin**: `tauri-plugin-updater` for automatic updates
- **Update Server**: GitHub Releases or custom update server
- **Update Flow**: Check for updates on launch → download in background → prompt user to install

**Rationale**:
- **User Experience**: Seamless updates without manual downloads
- **Security**: Signed updates with signature verification
- **Cross-Platform**: Works on macOS, Windows, Linux

**Update Manifest** (served from GitHub Releases or custom server):
```json
{
  "version": "1.1.0",
  "notes": "Bug fixes and performance improvements",
  "pub_date": "2025-12-15T12:00:00Z",
  "platforms": {
    "darwin-x86_64": {
      "signature": "...",
      "url": "https://github.com/user/jterm/releases/download/v1.1.0/jterm_1.1.0_x64.dmg"
    },
    "windows-x86_64": {
      "signature": "...",
      "url": "https://github.com/user/jterm/releases/download/v1.1.0/jterm_1.1.0_x64.msi"
    },
    "linux-x86_64": {
      "signature": "...",
      "url": "https://github.com/user/jterm/releases/download/v1.1.0/jterm_1.1.0_amd64.AppImage"
    }
  }
}
```

**Fallback**: If auto-update fails, notify user to download from website

---

## 10. Build and Distribution

### Decision: Platform-Specific Installers via Tauri Bundler

**Installers**:
- **macOS**: DMG (drag-to-Applications) or PKG (system installer)
- **Windows**: MSI (Windows Installer) with code signing
- **Linux**: AppImage (universal), DEB (Debian/Ubuntu), RPM (Fedora/RHEL)

**Rationale**:
- **User Expectations**: Platform-native installation experience
- **Code Signing**: Required for macOS notarization, recommended for Windows
- **Auto-Update Integration**: Works seamlessly with Tauri updater

**Build Process**:
```bash
# 1. Bundle Python backend with PyInstaller
scripts/build-python.sh
# Output: src-tauri/binaries/jterm-backend-{platform}

# 2. Build Tauri application with bundled Python
cargo tauri build
# Output: src-tauri/target/release/bundle/{dmg,msi,appimage,deb,rpm}

# 3. Sign and notarize (macOS)
xcrun notarytool submit jterm.dmg --apple-id ... --password ...

# 4. Upload to GitHub Releases or distribution server
```

**Bundle Size Estimates**:
- **Python Backend**: ~100-150MB (Python runtime + dependencies)
- **Tauri Runtime**: ~10-20MB (Rust binary + system WebView wrapper)
- **Assets**: ~5-10MB (icons, templates, static files)
- **Total**: 150-300MB installed size

---

## 11. Performance Optimization Strategies

### Decisions

**Startup Time Optimization**:
- **Lazy Loading**: Defer loading of non-essential xterm.js addons
- **Python Server**: Use `uvicorn --workers 1` for faster startup
- **Database**: Use in-memory cache for session history (restore from DB on demand)
- **Parallel Initialization**: Start Python server and Tauri window creation concurrently

**Runtime Performance**:
- **IPC Optimization**: Batch WebSocket messages for terminal output (100ms debouncing)
- **Memory Management**: Use Tauri's window-level isolation for multiple tabs
- **CPU Optimization**: Reuse web version's optimizations (1.0s PTY timeout, 60s ping interval)

**Bundle Size Optimization**:
- **PyInstaller**: Exclude unused modules (--exclude-module), strip debug symbols (--strip)
- **UPX Compression**: Compress Python executable with UPX (optional, 30-40% reduction)
- **Tauri**: Enable LTO (link-time optimization) and strip Rust binary

**Target Performance** (matching web version):
- Launch: <3 seconds cold start
- CPU: <5% idle, <15% active terminal, <25% recording playback
- Memory: <200MB base, <500MB with 10 tabs
- Bundle: 150-300MB installed

---

## 12. Testing Strategy

### Approach

**Unit Tests** (Rust):
- Test Tauri commands in isolation
- Test platform-specific PTY/clipboard/file dialog implementations
- Use mocking for OS APIs

**Integration Tests** (Rust + Python):
- Test Tauri ↔ Python communication
- Test Python backend launch and shutdown
- Test WebView loading and navigation

**E2E Tests** (Desktop-Specific):
- **Framework**: WebDriver (Tauri supports WebDriver protocol)
- **Test Scenarios**:
  - Launch app → verify window appears → verify terminal loads
  - Open file dialog → select file → verify file loads
  - Copy to clipboard → paste in external app → verify content
  - Create terminal tab → run command → verify output
  - Record session → playback → verify accuracy

**Performance Tests**:
- Launch time benchmarks
- CPU/memory profiling under various workloads
- Bundle size tracking

**Cross-Platform Tests**:
- Run E2E suite on macOS, Windows, Linux
- Verify platform-specific features (PTY, clipboard, menus)

---

## 13. Development Workflow

### Setup

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI
cargo install tauri-cli

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -r requirements.txt

# Initialize Tauri
cargo tauri init
```

### Development

```bash
# Terminal 1: Run Python backend (development mode)
uvicorn src.main:app --reload --port 8000

# Terminal 2: Run Tauri app (points to localhost:8000)
cargo tauri dev
```

### Building

```bash
# Bundle Python backend with PyInstaller
./scripts/build-python.sh

# Build Tauri app with bundled Python
cargo tauri build
```

### Testing

```bash
# Rust unit tests
cargo test

# Python unit tests
pytest tests/

# E2E tests (requires built app)
./scripts/test-e2e.sh
```

---

## 14. Migration Path for Existing Users

### Strategy

**Database Migration**:
1. Check for existing `webterminal.db` in project directory (web version)
2. If found, copy to platform-standard location (e.g., `~/Library/Application Support/jterm/`)
3. Preserve all user data (sessions, recordings, media, preferences)
4. Show migration success notification

**Settings Migration**:
- Themes, extensions, keyboard shortcuts automatically migrated with database
- No user action required

**Backwards Compatibility**:
- Desktop version can coexist with web version (different ports, database locations)
- Users can run both simultaneously if needed

---

## 15. Known Limitations and Mitigations

**Limitation 1: Two-Process Architecture**
- **Issue**: Tauri process + Python process = higher memory usage than single-process app
- **Impact**: ~20MB additional memory overhead
- **Mitigation**: Acceptable for desktop application; still well under 500MB total

**Limitation 2: Platform-Specific PTY Differences**
- **Issue**: Windows ConPTY behaves differently from Unix PTY
- **Impact**: Potential compatibility issues with specific terminal programs
- **Mitigation**: Extensive testing on all platforms; abstract PTY behind common interface; fallback to Python PTY if needed

**Limitation 3: Code Signing Requirements**
- **Issue**: macOS notarization requires Apple Developer account ($99/year)
- **Impact**: Cannot distribute notarized DMG without Developer account
- **Mitigation**: Provide unsigned DMG for testing; users can bypass Gatekeeper with right-click → Open

**Limitation 4: Bundle Size**
- **Issue**: 150-300MB installed size larger than web version
- **Impact**: Longer download times, more disk space
- **Mitigation**: Acceptable for desktop app standards (VS Code: 200MB, Slack: 150MB, Discord: 100MB)

**Limitation 5: WebView Differences**
- **Issue**: Different WebView engines on different platforms (WebKit on macOS, Edge WebView2 on Windows, WebKitGTK on Linux)
- **Impact**: Potential rendering differences or bugs
- **Mitigation**: Extensive cross-platform testing; avoid WebView-specific features; use standard web APIs

---

## Summary

All technical decisions have been made with clear rationale and trade-offs documented. The Tauri + PyInstaller architecture provides:

✅ **Code Reuse**: 80% of existing codebase preserved
✅ **Performance**: Matches web version targets (<5% CPU idle, <3s launch)
✅ **Bundle Size**: Smaller than Electron (150-300MB vs 300-500MB)
✅ **Cross-Platform**: Single codebase for macOS/Windows/Linux
✅ **Maintainability**: Existing test suite remains valid
✅ **Native Integration**: Platform-specific PTY, clipboard, file dialogs, menus
✅ **Security**: Tauri's security model + existing backend security

**Ready to proceed to Phase 1: Design & Contracts**
