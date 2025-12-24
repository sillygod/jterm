# Data Model: Desktop Application Conversion

**Feature**: 005-desktop-application
**Date**: 2025-12-13
**Status**: Complete

## Overview

This document defines the data model for the jterm desktop application. The desktop version **reuses the existing database schema** from the web version with minor modifications for desktop-specific paths and metadata.

**Key Principle**: Preserve backward compatibility with existing web version databases to enable seamless migration.

---

## Entity Relationship Diagram

```
UserProfile (1) ─┬─> (N) TerminalSession
                 ├─> (N) Recording
                 ├─> (N) MediaAsset
                 ├─> (N) ImageSession
                 ├─> (N) ThemeConfiguration
                 └─> (N) Extension

TerminalSession (1) ─┬─> (N) Recording
                     ├─> (N) MediaAsset
                     ├─> (1) AIContext
                     └─> (N) PerformanceSnapshot

Recording (1) ─> (N) RecordingEvent (embedded in events JSON array)

ImageSession (1) ─┬─> (1) AnnotationLayer
                  ├─> (N) EditOperation
                  └─> (N) SessionHistory

MediaAsset (1) ─> (N) SecurityScan (embedded)
```

---

## Core Entities

### 1. UserProfile

**Description**: Represents the desktop application user with preferences and settings.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)
- Desktop version enforces single default user (UUID: `00000000-0000-0000-0000-000000000001`)
- No multi-user authentication required for desktop

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| user_id | UUID | PK, NOT NULL | Unique user identifier |
| username | String(255) | UNIQUE, NOT NULL | User's display name |
| created_at | DateTime | NOT NULL | Account creation timestamp |
| last_login_at | DateTime | NULL | Last application launch |
| preferences | JSON | NOT NULL | User preferences (theme, shell, working_dir, shortcuts, AI config, recording config) |
| storage_quota_mb | Integer | NOT NULL, DEFAULT 1024 | Storage quota in MB |
| storage_used_mb | Integer | NOT NULL, DEFAULT 0 | Current storage usage in MB |
| active_theme_id | UUID | FK(ThemeConfiguration), NULL | Currently active theme |

**Validation Rules**:
- `storage_used_mb` ≤ `storage_quota_mb` (enforced in application, warning at 90%)
- `preferences` must be valid JSON with schema validation

**Indexes**:
- Primary key on `user_id`
- Unique index on `username`

---

### 2. TerminalSession

**Description**: Represents an active terminal tab with PTY process information.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)
- PTY process managed by Python backend (same as web version, no changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| session_id | UUID | PK, NOT NULL | Unique session identifier |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| status | Enum | NOT NULL | Session status: ACTIVE, INACTIVE, TERMINATED, RECORDING |
| pty_pid | Integer | NULL | Process ID of PTY (managed by Tauri) |
| created_at | DateTime | NOT NULL | Session creation timestamp |
| last_active_at | DateTime | NOT NULL | Last activity timestamp |
| terminated_at | DateTime | NULL | Session termination timestamp |
| shell_type | String(50) | NOT NULL | Shell type: bash, zsh, fish, powershell |
| working_directory | String(1024) | NOT NULL | Current working directory |
| cols | Integer | NOT NULL, DEFAULT 80 | Terminal columns (20-500) |
| rows | Integer | NOT NULL, DEFAULT 24 | Terminal rows (5-200) |
| environment_vars | JSON | NOT NULL | Environment variables |
| metadata | JSON | NULL | Additional session metadata |

**Validation Rules**:
- `status` ∈ {ACTIVE, INACTIVE, TERMINATED, RECORDING}
- `cols` ∈ [20, 500]
- `rows` ∈ [5, 200]
- `shell_type` ∈ {bash, zsh, fish, powershell} (platform-specific validation)

**State Transitions**:
```
ACTIVE → INACTIVE (tab switch)
ACTIVE → RECORDING (start recording)
ACTIVE → TERMINATED (close tab)
INACTIVE → ACTIVE (tab switch back)
RECORDING → ACTIVE (stop recording)
RECORDING → TERMINATED (close tab while recording)
```

**Indexes**:
- Primary key on `session_id`
- Index on `(user_id, status)` for active session queries
- Index on `created_at` for chronological ordering
- Index on `last_active_at` for recent activity queries

---

### 3. Recording

**Description**: Represents a captured terminal session with playback support.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)
- Export path uses platform-specific file dialogs (implementation detail, no schema change)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| recording_id | UUID | PK, NOT NULL | Unique recording identifier |
| session_id | UUID | FK(TerminalSession), NOT NULL | Source session |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| status | Enum | NOT NULL | Recording status: RECORDING, STOPPED, PROCESSING, READY, FAILED |
| started_at | DateTime | NOT NULL | Recording start timestamp |
| stopped_at | DateTime | NULL | Recording stop timestamp |
| duration_ms | Integer | NULL | Recording duration in milliseconds |
| events | JSON | NOT NULL | Array of recording events (timestamped I/O, resize, commands) |
| checkpoints | JSON | NULL | Array of seek points for playback |
| compression_ratio | Float | NULL | GZIP compression ratio (0.0-1.0) |
| file_size_bytes | Integer | NULL | Compressed recording size |
| metadata | JSON | NULL | Additional recording metadata |

**Validation Rules**:
- `status` ∈ {RECORDING, STOPPED, PROCESSING, READY, FAILED}
- `duration_ms` > 0 (when READY)
- `compression_ratio` ∈ [0.0, 1.0]
- `file_size_bytes` > 0 (when READY)

**Event Structure** (JSON):
```json
{
  "events": [
    {
      "timestamp_ms": 0,
      "type": "output",
      "data": "user@host:~$ "
    },
    {
      "timestamp_ms": 1234,
      "type": "input",
      "data": "ls -la\n"
    },
    {
      "timestamp_ms": 1250,
      "type": "resize",
      "cols": 120,
      "rows": 30
    },
    {
      "timestamp_ms": 2000,
      "type": "command",
      "command": "ls -la"
    }
  ],
  "checkpoints": [
    {"timestamp_ms": 0, "description": "Start"},
    {"timestamp_ms": 10000, "description": "10s mark"}
  ]
}
```

**Retention Policy**:
- Recordings older than 30 days automatically deleted
- Cleanup job runs daily

**Indexes**:
- Primary key on `recording_id`
- Index on `(user_id, status)` for user's recordings
- Index on `session_id` for session's recordings
- Index on `started_at` for chronological ordering

---

### 4. MediaAsset

**Description**: Represents uploaded or viewed media (images, videos, PDFs, EPUBs, HTML, documents).

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)
- File paths use platform-specific absolute paths (implementation detail, no schema change)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| asset_id | UUID | PK, NOT NULL | Unique asset identifier |
| session_id | UUID | FK(TerminalSession), NOT NULL | Source session |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| asset_type | Enum | NOT NULL | Asset type: IMAGE, VIDEO, HTML, DOCUMENT |
| file_path | String(2048) | NOT NULL | Absolute file path (platform-specific) |
| mime_type | String(128) | NOT NULL | MIME type (e.g., image/png, video/mp4) |
| file_size_bytes | Integer | NOT NULL | File size in bytes |
| dimensions | JSON | NULL | Image/video dimensions: {width, height} |
| duration_ms | Integer | NULL | Video/audio duration in milliseconds |
| created_at | DateTime | NOT NULL | Asset creation timestamp |
| last_accessed_at | DateTime | NOT NULL | Last access timestamp |
| access_count | Integer | NOT NULL, DEFAULT 0 | Number of times accessed |
| is_temporary | Boolean | NOT NULL, DEFAULT FALSE | Temporary asset (cleanup after session) |
| expires_at | DateTime | NULL | Expiration timestamp (for temporary assets) |
| security_status | Enum | NOT NULL, DEFAULT 'PENDING' | Security scan status: SAFE, SUSPICIOUS, MALICIOUS, PENDING |
| metadata | JSON | NULL | Additional asset metadata |

**Validation Rules**:
- `asset_type` ∈ {IMAGE, VIDEO, HTML, DOCUMENT}
- `file_size_bytes` ≤ 50MB for VIDEO, ≤ 10MB for IMAGE, ≤ 50MB for DOCUMENT, ≤ 5MB for HTML
- `security_status` ∈ {SAFE, SUSPICIOUS, MALICIOUS, PENDING}
- `mime_type` must match `asset_type` (e.g., IMAGE requires image/*)

**Cleanup Rules**:
- Temporary assets deleted when `expires_at` < NOW
- Assets with `access_count` = 0 and `created_at` > 30 days deleted

**Indexes**:
- Primary key on `asset_id`
- Index on `(user_id, asset_type)` for user's media by type
- Index on `session_id` for session's media
- Index on `created_at` for chronological ordering
- Index on `is_temporary, expires_at` for cleanup queries

---

### 5. ImageSession

**Description**: Represents an active image editing session.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)
- Clipboard source uses platform-specific clipboard APIs (implementation detail, no schema change)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| session_id | UUID | PK, NOT NULL | Unique session identifier |
| terminal_session_id | UUID | FK(TerminalSession), NOT NULL | Parent terminal session |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| source_type | Enum | NOT NULL | Source: FILE, CLIPBOARD, URL |
| source_path | String(2048) | NULL | Source file path or URL |
| image_format | String(10) | NOT NULL | Image format: png, jpeg, gif, webp, bmp |
| width | Integer | NOT NULL | Image width in pixels |
| height | Integer | NOT NULL | Image height in pixels |
| created_at | DateTime | NOT NULL | Session creation timestamp |
| last_modified_at | DateTime | NOT NULL | Last modification timestamp |
| is_modified | Boolean | NOT NULL, DEFAULT FALSE | Has unsaved changes |
| temp_file_path | String(2048) | NULL | Temporary file path for edits |

**Validation Rules**:
- `source_type` ∈ {FILE, CLIPBOARD, URL}
- `image_format` ∈ {png, jpeg, gif, webp, bmp}
- `width`, `height` > 0
- `source_path` NOT NULL when `source_type` ∈ {FILE, URL}

**Retention Policy**:
- Sessions older than 7 days automatically deleted
- Cleanup job runs daily

**Indexes**:
- Primary key on `session_id`
- Index on `(user_id, created_at DESC)` for recent sessions
- Index on `terminal_session_id` for session's image editors

---

### 6. AnnotationLayer

**Description**: Represents drawing annotations on an image (Fabric.js canvas JSON).

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| layer_id | UUID | PK, NOT NULL | Unique layer identifier |
| image_session_id | UUID | FK(ImageSession), UNIQUE, NOT NULL | Parent image session (1:1) |
| canvas_json | JSONB | NOT NULL | Fabric.js canvas state (compressed with GZIP) |
| version | Integer | NOT NULL, DEFAULT 1 | Layer version for optimistic locking |
| last_updated_at | DateTime | NOT NULL | Last update timestamp |

**Canvas JSON Structure** (Fabric.js format):
```json
{
  "version": "5.3.0",
  "objects": [
    {
      "type": "path",
      "stroke": "#ff0000",
      "strokeWidth": 5,
      "path": [["M", 10, 10], ["L", 100, 100]]
    },
    {
      "type": "text",
      "text": "Hello",
      "left": 50,
      "top": 50,
      "fill": "#000000"
    }
  ]
}
```

**Indexes**:
- Primary key on `layer_id`
- Unique index on `image_session_id` (one layer per session)

---

### 7. EditOperation

**Description**: Represents a single undo/redo operation in the image editor.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| operation_id | UUID | PK, NOT NULL | Unique operation identifier |
| image_session_id | UUID | FK(ImageSession), NOT NULL | Parent image session |
| operation_type | Enum | NOT NULL | Operation type: DRAW, TEXT, SHAPE, FILTER, CROP, RESIZE |
| operation_index | Integer | NOT NULL | Position in undo/redo stack (0-49) |
| canvas_snapshot | JSONB | NOT NULL | Canvas state snapshot (GZIP compressed) |
| created_at | DateTime | NOT NULL | Operation timestamp |

**Validation Rules**:
- `operation_type` ∈ {DRAW, TEXT, SHAPE, FILTER, CROP, RESIZE}
- `operation_index` ∈ [0, 49] (50-operation circular buffer)

**Undo/Redo Logic**:
- Operations stored in circular buffer (max 50)
- Undo: Restore `canvas_snapshot` at `operation_index - 1`
- Redo: Restore `canvas_snapshot` at `operation_index + 1`
- New operation: Discard all operations after current index

**Indexes**:
- Primary key on `operation_id`
- Index on `(image_session_id, operation_index)` for stack queries

---

### 8. SessionHistory

**Description**: Represents quick-access history of recently viewed/edited images.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| history_id | UUID | PK, NOT NULL | Unique history identifier |
| terminal_session_id | UUID | FK(TerminalSession), NOT NULL | Parent terminal session |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| image_path | String(2048) | NOT NULL | Image file path |
| view_count | Integer | NOT NULL, DEFAULT 1 | Number of times viewed |
| is_edited | Boolean | NOT NULL, DEFAULT FALSE | Has been edited |
| last_viewed_at | DateTime | NOT NULL | Last view timestamp |
| created_at | DateTime | NOT NULL | First view timestamp |

**Validation Rules**:
- Unique constraint on `(terminal_session_id, image_path)` (one history entry per image per session)
- Maximum 20 entries per terminal session (LRU eviction)

**Retention Policy**:
- History entries older than 7 days automatically deleted
- Cleanup job runs daily

**Indexes**:
- Primary key on `history_id`
- Unique index on `(terminal_session_id, image_path)`
- Index on `(user_id, last_viewed_at DESC)` for recent history queries

---

### 9. AIContext

**Description**: Represents AI conversation history for a terminal session.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| context_id | UUID | PK, NOT NULL | Unique context identifier |
| session_id | UUID | FK(TerminalSession), UNIQUE, NOT NULL | Parent session (1:1) |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| provider | Enum | NOT NULL | AI provider: OPENAI, ANTHROPIC, GROQ, OLLAMA, CUSTOM |
| model | String(128) | NOT NULL | Model name (e.g., gpt-4, claude-3-sonnet) |
| messages | JSON | NOT NULL | Array of conversation messages |
| created_at | DateTime | NOT NULL | Context creation timestamp |
| last_updated_at | DateTime | NOT NULL | Last message timestamp |
| metadata | JSON | NULL | Additional context metadata |

**Validation Rules**:
- `provider` ∈ {OPENAI, ANTHROPIC, GROQ, OLLAMA, CUSTOM}

**Messages Structure** (JSON):
```json
{
  "messages": [
    {
      "role": "user",
      "content": "How do I list files in Linux?",
      "timestamp": "2025-12-13T10:00:00Z",
      "tokens": 10,
      "processing_time_ms": 50
    },
    {
      "role": "assistant",
      "content": "Use the `ls` command...",
      "timestamp": "2025-12-13T10:00:02Z",
      "tokens": 45,
      "processing_time_ms": 1500
    }
  ]
}
```

**Indexes**:
- Primary key on `context_id`
- Unique index on `session_id` (one context per session)
- Index on `(user_id, last_updated_at DESC)` for recent conversations

---

### 10. PerformanceSnapshot

**Description**: Represents system metrics at a point in time.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| snapshot_id | UUID | PK, NOT NULL | Unique snapshot identifier |
| session_id | UUID | FK(TerminalSession), NULL | Associated session (NULL for app-level) |
| user_id | UUID | FK(UserProfile), NOT NULL | Owner user |
| timestamp | DateTime | NOT NULL | Snapshot timestamp |
| cpu_percent | Float | NOT NULL | CPU usage percentage (0.0-100.0) |
| memory_mb | Float | NOT NULL | Memory usage in MB |
| active_connections | Integer | NOT NULL | Active WebSocket connections |
| terminal_updates_per_sec | Float | NULL | Terminal update rate |
| metadata | JSON | NULL | Additional metrics |

**Validation Rules**:
- `cpu_percent` ∈ [0.0, 100.0]
- `memory_mb` > 0
- `active_connections` ≥ 0

**Retention Policy**:
- Snapshots older than 24 hours automatically deleted
- Cleanup job runs hourly

**Indexes**:
- Primary key on `snapshot_id`
- Index on `(user_id, timestamp DESC)` for recent metrics
- Index on `session_id` for session-specific metrics
- Index on `timestamp` for time-range queries

---

### 11. ThemeConfiguration

**Description**: Represents color schemes and UI customization.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| theme_id | UUID | PK, NOT NULL | Unique theme identifier |
| theme_name | String(255) | UNIQUE, NOT NULL | Theme display name |
| is_builtin | Boolean | NOT NULL, DEFAULT FALSE | Built-in theme (cannot be deleted) |
| theme_definition | JSON | NOT NULL | Theme colors, fonts, UI elements |
| created_at | DateTime | NOT NULL | Theme creation timestamp |
| created_by_user_id | UUID | FK(UserProfile), NULL | Creator (NULL for built-in) |

**Theme Definition Structure** (JSON):
```json
{
  "colors": {
    "background": "#1e1e1e",
    "foreground": "#d4d4d4",
    "cursor": "#ffffff",
    "selection": "#264f78",
    "black": "#000000",
    "red": "#cd3131",
    "green": "#0dbc79",
    "yellow": "#e5e510",
    "blue": "#2472c8",
    "magenta": "#bc3fbc",
    "cyan": "#11a8cd",
    "white": "#e5e5e5"
  },
  "fonts": {
    "family": "Menlo, Monaco, 'Courier New', monospace",
    "size": 14,
    "lineHeight": 1.2
  },
  "ui": {
    "borderRadius": 4,
    "padding": 8
  }
}
```

**Indexes**:
- Primary key on `theme_id`
- Unique index on `theme_name`

---

### 12. Extension

**Description**: Represents installed plugins with manifest validation.

**Desktop Modifications**:
- ✅ **REUSED** from web version (no schema changes)

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| extension_id | UUID | PK, NOT NULL | Unique extension identifier |
| extension_name | String(255) | UNIQUE, NOT NULL | Extension display name |
| version | String(50) | NOT NULL | Extension version (semver) |
| is_enabled | Boolean | NOT NULL, DEFAULT TRUE | Extension enabled status |
| manifest | JSON | NOT NULL | Extension manifest (name, version, permissions, entry point) |
| installed_at | DateTime | NOT NULL | Installation timestamp |
| installed_by_user_id | UUID | FK(UserProfile), NOT NULL | Installer user |

**Manifest Structure** (JSON):
```json
{
  "name": "My Extension",
  "version": "1.0.0",
  "description": "Does something cool",
  "author": "John Doe",
  "permissions": ["terminal", "media", "clipboard"],
  "entry_point": "extensions/my-extension/main.js"
}
```

**Validation Rules**:
- `version` must match semver format (e.g., 1.0.0)
- `manifest.permissions` must be subset of allowed permissions

**Indexes**:
- Primary key on `extension_id`
- Unique index on `extension_name`

---

## Desktop-Specific Considerations

### Platform-Specific Paths

**Database Location**:
- **macOS**: `~/Library/Application Support/jterm/webterminal.db`
- **Windows**: `%APPDATA%\jterm\webterminal.db`
- **Linux**: `~/.local/share/jterm/webterminal.db`

**Media Assets**:
- **macOS**: `~/Library/Application Support/jterm/media/`
- **Windows**: `%APPDATA%\jterm\media\`
- **Linux**: `~/.local/share/jterm/media/`

**Temporary Files**:
- **macOS**: `~/Library/Caches/jterm/temp/`
- **Windows**: `%LOCALAPPDATA%\jterm\temp\`
- **Linux**: `~/.cache/jterm/temp/`

### Migration Strategy

**Web → Desktop Migration**:
1. On first desktop launch, check for existing `webterminal.db` in project directory
2. If found, copy to platform-specific location
3. Update all file paths in `MediaAsset` and `ImageSession` to absolute paths
4. Preserve all user data (sessions, recordings, preferences)
5. Show migration success notification

**Schema Version Tracking**:
- Use Alembic migrations (existing mechanism)
- Desktop version shares migration history with web version
- No desktop-specific migrations required (100% schema compatibility)

### Cleanup Jobs

**Scheduled Tasks** (run by Python backend - REUSED from web version):
- **Daily**: Delete recordings older than 30 days
- **Daily**: Delete image sessions older than 7 days
- **Daily**: Delete temporary media assets (expired)
- **Hourly**: Delete performance snapshots older than 24 hours

**Implementation**:
```python
# src/main.py (existing lifespan manager)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await verify_database_connection()
    await create_default_user()
    await restore_session_history_cache()

    # Start background cleanup job (EXISTING - no changes needed)
    cleanup_task = asyncio.create_task(run_cleanup_jobs())

    yield

    # Shutdown
    cleanup_task.cancel()
```

**Desktop Note**: Cleanup jobs run in the bundled Python backend automatically - no Tauri involvement required. This is the same mechanism as the web version.

---

## Summary

The desktop application **reuses 100% of the existing database schema** from the web version with no schema modifications. All changes are implementation details (platform-specific file paths) that do not require schema changes.

**Key Benefits**:
- ✅ **Backward Compatibility**: Seamless migration from web to desktop
- ✅ **Code Reuse**: All SQLAlchemy models unchanged (100% reused)
- ✅ **Data Preservation**: No data loss during migration
- ✅ **Testing**: Existing database tests remain valid (100% reused)
- ✅ **Business Logic Reuse**: PTY service, cleanup jobs, all Python backend logic unchanged

**Desktop-Specific Adaptations** (implementation-only, no schema changes):
- Database stored in platform-standard locations (macOS: ~/Library/Application Support, Windows: %APPDATA%, Linux: ~/.local/share)
- File paths use platform-specific absolute paths
- Cleanup jobs run by Python backend (same as web version, no changes)
- PTY processes managed by Python backend (same as web version, no changes)

**What Tauri Handles** (native-only features):
- Application lifecycle (launch, quit)
- Native clipboard (system clipboard API)
- Native file dialogs (OS file picker)
- Native menus (OS menu bar)
- System integration (window title, notifications)

**What Python Handles** (business logic - 100% reused):
- All database operations
- All PTY operations (terminal I/O)
- All media processing
- All recording operations
- All AI assistant operations
- All cleanup jobs
- All WebSocket communication

**Ready to proceed to implementation**
