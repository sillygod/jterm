# Version Migration Notes: Tauri v2.9.6

**Date**: 2025-12-14
**Reason**: Installed latest Tauri version (v2.9.6) instead of originally planned v1.5

## Summary of Changes

During implementation setup (tasks T001-T007), we installed **Tauri v2.9.6** instead of the originally planned **Tauri v1.5**. This required updating Rust to v1.92.0 to support edition2024.

---

## Version Differences

### Before (Original Plan)
- **Tauri Version**: 1.5+
- **Rust Version**: 1.75+
- **Tauri Architecture**: Monolithic with features
- **Plugin System**: N/A (features-based)

### After (Actual Implementation)
- **Tauri Version**: 2.9.6
- **Rust Version**: 1.92.0 (requires 1.85+ for edition2024)
- **Tauri Architecture**: Plugin-based architecture
- **Plugin System**: Separate plugin packages

---

## Key API Differences

### Dependency Changes

**Tauri v1.5 (Original)**:
```toml
[dependencies]
tauri = { version = "1.5", features = ["api-all", "dialog-all", "clipboard-all", "shell-open"] }
tauri-build = { version = "1.5", features = [] }
```

**Tauri v2.9 (Updated)**:
```toml
[dependencies]
tauri = { version = "2.9", features = [] }
tauri-plugin-dialog = "2.0"
tauri-plugin-clipboard-manager = "2.0"
tauri-plugin-shell = "2.0"
tauri-build = { version = "2.0", features = [] }
```

### Configuration Changes

**Tauri v1 Config** (`tauri.conf.json`):
- Uses `allowlist` for permissions
- Features enabled via nested configuration

**Tauri v2 Config** (`tauri.conf.json`):
- Uses `permissions` array
- Plugin-based capabilities
- More granular permission model

### JavaScript API Changes

**Tauri v1**:
```javascript
import { invoke } from '@tauri-apps/api/tauri';
import { open } from '@tauri-apps/api/dialog';
import { writeText } from '@tauri-apps/api/clipboard';
```

**Tauri v2**:
```javascript
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';
import { writeText } from '@tauri-apps/plugin-clipboard-manager';
```

---

## Files Updated

All specification files have been updated to reflect Tauri v2.9.6:

### 1. **research.md**
- Line 15: Changed "Tauri 1.5+" to "Tauri 2.9+"

### 2. **plan.md**
- Line 15: Updated Rust requirement to 1.85+ (edition2024 support)
- Line 20: Changed "Tauri 1.5+" to "Tauri 2.9+"

### 3. **quickstart.md**
- Line 13: Updated Rust requirement to 1.85+
- Line 60: Updated version check expectation to 1.85+
- Line 116: Updated Tauri CLI version check to 2.9+
- Lines 255-263: Updated dependencies to use Tauri 2.9 plugin architecture

### 4. **UPDATES.md**
- Lines 217-223: Updated dependency example to show Tauri 2.9 plugins

### 5. **tasks.md**
- Line 28: Marked T001 as completed, updated Rust version requirement
- Line 30: Marked T003 as completed

---

## Migration Benefits

### Improvements in Tauri v2

1. **Better Security**: More granular permission model with plugin-based capabilities
2. **Smaller Bundle Size**: Only include plugins you actually use
3. **Better Performance**: Optimized IPC and reduced overhead
4. **Better Mobile Support**: Improved Android/iOS support (future-proof)
5. **Better Developer Experience**: Clearer API separation, better TypeScript types

### Breaking Changes (None for Our Use Case)

Since we're starting from scratch, we don't have any breaking changes to handle. All planning documents have been proactively updated to use Tauri v2 APIs.

---

## Implementation Impact

### No Changes Required
- Python backend: 100% unchanged
- PTY architecture: 100% unchanged (still uses Python service)
- Database schema: 100% unchanged
- Frontend UI: 100% unchanged (xterm.js, Fabric.js, etc.)

### Minor Changes Required
- Tauri command implementations: Use v2 API patterns
- JavaScript Tauri API calls: Import from plugin packages
- Configuration files: Use v2 config structure

---

## Action Items

### For Task Implementation

When implementing tasks T004-T007 and beyond:

1. **T004 (Tauri Init)**: Use `cargo tauri init` (v2 command structure)
2. **T006 (tauri.conf.json)**: Use v2 configuration format
3. **T007 (package.json)**: Add v2 JavaScript packages:
   - `@tauri-apps/api` v2
   - `@tauri-apps/plugin-dialog` v2
   - `@tauri-apps/plugin-clipboard-manager` v2
   - `@tauri-apps/plugin-shell` v2

4. **Phase 2+ Tasks**: Reference Tauri v2 documentation at https://v2.tauri.app/

---

## References

- **Tauri v2 Documentation**: https://v2.tauri.app/
- **Migration Guide**: https://v2.tauri.app/start/migrate/from-tauri-1/
- **Plugin Documentation**: https://v2.tauri.app/plugin/
- **Breaking Changes**: https://v2.tauri.app/blog/tauri-2-0/#breaking-changes

---

## Verification

Installed versions verified on 2025-12-14:
- ✅ Rust: 1.92.0 (ded5c06cf 2025-12-08)
- ✅ Cargo: 1.92.0 (8f40fc59f 2024-08-21)
- ✅ Tauri CLI: 2.9.6
- ✅ PyInstaller: 6.17.0
- ✅ Python: 3.11.8
