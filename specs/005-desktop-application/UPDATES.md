# Planning Updates: Python PTY Reuse

**Date**: 2025-12-13
**Reason**: User feedback to maximize code reuse by using existing Python PTY service instead of reimplementing in Rust

## Summary of Changes

The planning documents have been updated to reflect a better architectural decision: **reuse the existing Python PTY service** instead of implementing PTY operations in Rust/Tauri. This significantly increases code reuse and simplifies the architecture.

---

## Key Improvements

### Before (Original Plan)
- **Code Reuse**: 80%
- **Rust Codebase**: ~5,000 lines
- **JavaScript**: ~1,000 lines
- **Tauri Commands**: 31 commands (including 6 PTY commands)
- **PTY Implementation**: Duplicate in Rust with platform-specific code

### After (Updated Plan)
- **Code Reuse**: 90% ✅ (+10% improvement)
- **Rust Codebase**: ~3,000 lines ✅ (40% reduction)
- **JavaScript**: ~500 lines ✅ (50% reduction)
- **Tauri Commands**: 25 commands ✅ (removed 6 PTY commands)
- **PTY Implementation**: Reuse existing Python service ✅ (zero duplication)

---

## Files Updated

### 1. research.md
**Section**: "4. PTY Integration"

**Changes**:
- ❌ **Removed**: Rust PTY implementation approach
- ✅ **Added**: Justification for reusing Python PTY service
- ✅ **Added**: Communication flow diagram (unchanged from web version)
- ✅ **Added**: Benefits list (code reuse, battle-tested, no duplication, simpler architecture)

**Key Rationale**:
- Python PTY already optimized (1.0s timeout, 99.9% CPU reduction)
- Already handles platform differences (macOS, Windows, Linux)
- No performance benefit from Rust implementation
- Avoid maintaining two PTY implementations

---

### 2. contracts/tauri-commands.md
**Sections Removed**:
- "2. Terminal/PTY Commands" (entire section with 6 commands)
  - ~~create_pty~~
  - ~~write_pty~~
  - ~~read_pty~~
  - ~~resize_pty~~
  - ~~kill_pty~~

**Changes**:
- Command categories: 6 → 5
- Total commands: 31 → 25
- Updated error handling example (PTY → file dialog)
- Updated summary to explain PTY is handled by Python backend

**Remaining Commands** (25 total):
1. Application Lifecycle (3): app_ready, get_database_path, quit_app
2. Clipboard (4): get/set text, get/set image
3. File Dialogs (3): select file, select directory, save file
4. Menu (2): update menu item, show context menu
5. System Integration (13): open URL, show in folder, system info, window title, notifications, etc.

---

### 3. plan.md
**Section**: "Technical Context - Scale/Scope"

**Changes**:
- Rust codebase: ~5,000 → ~3,000 lines
- JavaScript: ~1,000 → ~500 lines
- Platform-specific code: ~20% → ~10%
- Code reuse: ~80% → ~90%

**Section**: "Project Structure"

**Changes**:
- Removed `src-tauri/src/platform/` (PTY platform code)
- Removed `src-tauri/src/commands/terminal.rs`
- Simplified to 4 command modules: clipboard, file_dialogs, menu, system
- Reduced UI adaptations: ~1,000 → ~500 lines

**Section**: "Key Integration Points"

**Changes**:
- Clarified that Python backend handles ALL business logic including PTY
- Tauri only exposes native-only operations
- Frontend uses WebSocket for terminal I/O (unchanged from web version)

**Section**: "Benefits"

**Changes**:
- Code reuse: 80% → 90%
- Added: "No PTY duplication"
- Added: "Simpler architecture (no Rust-Python IPC for terminal)"
- Added: "Existing PTY tests 100% valid"

---

### 4. data-model.md
**Section**: "TerminalSession - Desktop Modifications"

**Changes**:
- Before: "PTY process managed by Tauri Rust code"
- After: "PTY process managed by Python backend (same as web version, no changes)"

**Section**: "Cleanup Jobs"

**Changes**:
- Before: "Scheduled Tasks (run by Tauri Rust code)"
- After: "Scheduled Tasks (run by Python backend - REUSED from web version)"
- Removed Rust implementation example
- Added Python implementation example (existing lifespan manager)

**Section**: "Summary"

**Changes**:
- Removed references to "PTY management in Rust"
- Removed references to "Cleanup jobs run by Tauri"
- Added clear separation: "What Tauri Handles" vs "What Python Handles"
- Emphasized 100% reuse of Python business logic

---

## Architecture Comparison

### Original Design
```
User Input
  ↓
JavaScript (xterm.js)
  ↓
Tauri Command (write_pty) ❌ Extra layer
  ↓
Rust PTY Implementation ❌ Duplication
  ↓
OS PTY API
```

### Updated Design
```
User Input
  ↓
JavaScript (xterm.js)
  ↓
WebSocket (/ws/terminal) ✅ Same as web version
  ↓
Python PTY Service ✅ Reused, battle-tested
  ↓
OS PTY API
```

---

## Benefits Realized

### Development
- **Less Code**: 2,500 fewer lines to write and maintain
- **No Duplication**: Single PTY implementation in Python
- **Faster Development**: Don't need to rewrite/test PTY in Rust

### Maintenance
- **Single Source**: PTY updates only needed once in Python
- **Bug Fixes**: Desktop inherits all PTY fixes automatically
- **Consistency**: Desktop and web versions behave identically

### Testing
- **Existing Tests**: 100% of PTY tests remain valid
- **No New Tests**: Don't need Rust PTY tests
- **Integration Tests**: Simpler (no Rust-Python PTY bridge to test)

### Performance
- **Same Performance**: Python PTY already optimized (<5% CPU idle)
- **Less Overhead**: No Tauri-Python IPC for terminal I/O
- **Proven**: 99.9% CPU reduction already achieved in web version

---

## What This Means for Implementation

### Rust Work Reduced
- ❌ Don't implement: Platform-specific PTY backends (macOS, Windows, Linux)
- ❌ Don't implement: PTY lifecycle management
- ❌ Don't implement: PTY I/O handling
- ❌ Don't implement: PTY resize handling
- ✅ Only implement: 25 Tauri commands for native features

### Python Work Unchanged
- ✅ Reuse: Entire PTY service (src/services/pty_service.py)
- ✅ Reuse: Terminal WebSocket handler (src/websockets/terminal_handler.py)
- ✅ Reuse: All existing optimizations (1.0s timeout, debouncing, etc.)

### Frontend Work Minimal
- ✅ Reuse: xterm.js integration (static/js/terminal.js)
- ✅ Reuse: WebSocket protocol (same as web version)
- ✅ Add: ~500 lines for Tauri API calls (clipboard, file dialogs, menus)

---

## Updated Tauri Dependencies

### Before (with PTY)
```toml
[dependencies]
nix = { version = "0.27", features = ["pty"] }  # ❌ Not needed
windows = { version = "0.51", features = ["Win32_System_Console"] }  # ❌ Not needed
```

### After (native-only)
```toml
[dependencies]
tauri = { version = "2.9", features = [] }  # ✅ Only native features
tauri-plugin-dialog = "2.0"
tauri-plugin-clipboard-manager = "2.0"
tauri-plugin-shell = "2.0"
```

**Dependencies Removed**: 2 (nix, windows)
**Complexity Reduced**: No platform-specific PTY code

---

## Conclusion

This architectural update **significantly simplifies the desktop implementation** while **increasing code reuse from 80% to 90%**. By recognizing that the Python PTY service is already battle-tested and optimized, we avoid unnecessary duplication and maintain a single source of truth for terminal operations.

**The desktop version now focuses exclusively on what it should do**: provide native OS integration (clipboard, file dialogs, menus) while letting the proven Python backend handle all business logic.

**Next Steps**: Proceed with `/speckit.tasks` to generate implementation tasks based on this improved architecture.
