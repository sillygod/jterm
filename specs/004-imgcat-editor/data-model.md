# Data Model: imgcat Image Editor

**Branch**: `004-imgcat-editor` | **Date**: 2025-11-12
**Purpose**: Define data structures, entities, and relationships for image editing feature

## Overview

The image editor data model supports:
- Loading and managing image editing sessions
- Storing annotation layers and canvas state
- Undo/redo history management
- Session history for quick re-editing

## Entity Relationship Diagram

```
┌─────────────────┐
│  ImageSession   │
│                 │
│  id (PK)        │─────┐
│  terminal_id    │     │
│  image_source   │     │
│  created_at     │     │
│  last_modified  │     │
└─────────────────┘     │
                        │ 1:1
                        │
                ┌───────▼──────────┐
                │ AnnotationLayer  │
                │                  │
                │  id (PK)         │
                │  session_id (FK) │
                │  canvas_json     │      ┌─────────────────┐
                │  version         │      │ EditOperation   │
                └──────────────────┘      │                 │
                        │                 │  id (PK)        │
                        │ 1:N             │  session_id(FK) │
                        └─────────────────┤  operation_type │
                                          │  canvas_snapshot│
                                          │  timestamp      │
                                          │  position       │
                                          └─────────────────┘

┌─────────────────┐
│ SessionHistory  │
│                 │
│  id (PK)        │
│  terminal_id    │
│  image_path     │
│  last_viewed    │
│  view_count     │
└─────────────────┘
```

## Entities

### 1. ImageSession

Represents an active image editing session.

**Purpose**: Track the currently loaded image and its editing state.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | Primary Key, Not Null | Unique session identifier |
| `terminal_session_id` | String(255) | Not Null, Indexed | Terminal session ID from jterm |
| `image_source_type` | Enum | Not Null | Source type: 'file', 'clipboard', 'url' |
| `image_source_path` | String(1024) | Nullable | File path or URL (null for clipboard) |
| `image_format` | String(10) | Not Null | Image format: 'png', 'jpeg', 'gif', 'webp', 'bmp' |
| `image_width` | Integer | Not Null | Original image width in pixels |
| `image_height` | Integer | Not Null | Original image height in pixels |
| `image_size_bytes` | Integer | Not Null | File size in bytes |
| `temp_file_path` | String(1024) | Not Null | Path to temporary working copy |
| `created_at` | DateTime | Not Null | Session creation timestamp |
| `last_modified_at` | DateTime | Not Null | Last edit timestamp |
| `is_modified` | Boolean | Default: False | Whether image has unsaved edits |

**Indexes**:
- `idx_terminal_session` on `terminal_session_id` (for session history queries)
- `idx_created_at` on `created_at` (for cleanup jobs)

**Validation Rules**:
- `image_size_bytes` ≤ 52428800 (50MB limit from FR-023)
- `image_width` ≤ 32767 and `image_height` ≤ 32767 (Canvas API limits)
- `image_format` must be in ['png', 'jpeg', 'gif', 'webp', 'bmp'] (FR-020)

**State Transitions**:
```
Created → Modified → Saved/Copied
   ↓         ↓           ↓
   └─────────┴───────────→ Closed
```

---

### 2. AnnotationLayer

Stores the canvas annotation state using Fabric.js JSON serialization.

**Purpose**: Persist canvas objects (drawings, text, shapes) for save/restore operations.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | Primary Key, Not Null | Unique layer identifier |
| `session_id` | UUID | Foreign Key, Not Null | Reference to ImageSession |
| `canvas_json` | JSON/Text | Not Null | Fabric.js canvas serialization |
| `version` | Integer | Not Null | Increments on each save (optimistic locking) |
| `last_updated` | DateTime | Not Null | Timestamp of last update |

**Relationships**:
- `session_id` → `ImageSession.id` (One-to-One, Cascade Delete)

**JSON Structure** (canvas_json field):
```json
{
  "version": "5.3.0",
  "objects": [
    {
      "type": "path",
      "stroke": "#ff0000",
      "strokeWidth": 3,
      "path": [[...], [...]],
      ...
    },
    {
      "type": "i-text",
      "text": "Bug here",
      "fontSize": 20,
      "fill": "#000000",
      ...
    }
  ],
  "background": "..."
}
```

**Validation Rules**:
- `canvas_json` must be valid JSON
- `version` must increment monotonically
- JSON size should be reasonable (<10MB typical, alert if >50MB)

---

### 3. EditOperation

Represents a single edit operation in the undo/redo history stack.

**Purpose**: Enable undo/redo functionality by storing canvas state snapshots.

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | Primary Key, Not Null | Unique operation identifier |
| `session_id` | UUID | Foreign Key, Not Null | Reference to ImageSession |
| `operation_type` | Enum | Not Null | Type: 'draw', 'text', 'shape', 'filter', 'crop', 'resize' |
| `canvas_snapshot` | JSON/Text | Not Null | Fabric.js canvas state at this point |
| `timestamp` | DateTime | Not Null | When operation was performed |
| `position` | Integer | Not Null | Position in undo/redo stack (0-49) |

**Relationships**:
- `session_id` → `ImageSession.id` (Many-to-One, Cascade Delete)

**Indexes**:
- `idx_session_position` on (`session_id`, `position`) for fast undo/redo lookup

**Validation Rules**:
- Max 50 operations per session (enforced by circular buffer logic)
- `position` must be 0-49
- `canvas_snapshot` must be valid Fabric.js JSON

**Lifecycle**:
- Created: After each user edit operation completes
- Read: On undo/redo action
- Deleted: When session closes or oldest operations expire (>50 limit)

**Storage Strategy**:
- In-memory circular buffer (JavaScript) for active session
- SQLite for persistence across browser refreshes
- Cleanup on session close

---

### 4. SessionHistory

Tracks recently viewed/edited images for quick re-access.

**Purpose**: Enable `imgcat --history` and `imgcat -e N` commands (User Story 5).

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | Primary Key, Not Null | Unique history entry identifier |
| `terminal_session_id` | String(255) | Not Null, Indexed | Terminal session ID from jterm |
| `image_path` | String(1024) | Not Null | File path or URL of image |
| `image_source_type` | Enum | Not Null | Source: 'file', 'clipboard', 'url' |
| `thumbnail_path` | String(1024) | Nullable | Path to cached thumbnail (optional) |
| `last_viewed_at` | DateTime | Not Null | Most recent view timestamp |
| `view_count` | Integer | Default: 1 | Number of times viewed in this session |
| `is_edited` | Boolean | Default: False | Whether image was edited (vs just viewed) |

**Indexes**:
- `idx_terminal_last_viewed` on (`terminal_session_id`, `last_viewed_at` DESC) for history queries

**Unique Constraint**:
- (`terminal_session_id`, `image_path`) - One entry per image per terminal session

**Validation Rules**:
- Maximum 20 entries per `terminal_session_id` (LRU eviction)
- Cleanup entries older than 7 days

**Lifecycle**:
- Created/Updated: On each `imgcat` invocation
- Read: On `imgcat --history` command
- Deleted: On session cleanup (7 days) or terminal close

**In-Memory Representation**:
```python
# Python OrderedDict for LRU cache
session_histories = {
    "terminal_abc123": OrderedDict([
        ("image1.png", HistoryEntry(...)),
        ("image2.png", HistoryEntry(...)),
        ...
    ])
}
```

---

## Data Access Patterns

### 1. Load Image for Editing
```
User: imgcat screenshot.png

1. Check SessionHistory for terminal_session_id
2. Create ImageSession record
3. Create AnnotationLayer (empty canvas)
4. Add/Update SessionHistory entry
5. Return session_id to frontend
```

### 2. Perform Edit Operation
```
User: Draws annotation on canvas

1. Frontend: Serialize Fabric.js canvas to JSON
2. Backend: Store EditOperation snapshot
3. Backend: Update AnnotationLayer.canvas_json
4. Backend: Increment AnnotationLayer.version
5. Backend: Set ImageSession.is_modified = True
```

### 3. Undo Operation
```
User: Clicks Undo button

1. Frontend: Load previous EditOperation by position
2. Frontend: Restore canvas from canvas_snapshot JSON
3. Frontend: Decrement current position pointer
```

### 4. Save Image
```
User: Clicks Save button

1. Frontend: Export Fabric.js canvas to image data URL
2. Backend: Apply canvas to image using Pillow
3. Backend: Save to file system
4. Backend: Update ImageSession.is_modified = False
5. Backend: Clear EditOperation history
```

### 5. Load from History
```
User: imgcat --history, selects #2

1. Query SessionHistory by terminal_session_id
2. Get entry at position 2 (ordered by last_viewed_at DESC)
3. Load image from image_path
4. Create new ImageSession
5. Return session_id to frontend
```

---

## Database Schema (SQLite)

### Table: image_sessions

```sql
CREATE TABLE image_sessions (
    id TEXT PRIMARY KEY,
    terminal_session_id TEXT NOT NULL,
    image_source_type TEXT NOT NULL CHECK(image_source_type IN ('file', 'clipboard', 'url')),
    image_source_path TEXT,
    image_format TEXT NOT NULL CHECK(image_format IN ('png', 'jpeg', 'gif', 'webp', 'bmp')),
    image_width INTEGER NOT NULL CHECK(image_width > 0 AND image_width <= 32767),
    image_height INTEGER NOT NULL CHECK(image_height > 0 AND image_height <= 32767),
    image_size_bytes INTEGER NOT NULL CHECK(image_size_bytes <= 52428800),
    temp_file_path TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_modified BOOLEAN NOT NULL DEFAULT 0
);

CREATE INDEX idx_terminal_session ON image_sessions(terminal_session_id);
CREATE INDEX idx_created_at ON image_sessions(created_at);
```

### Table: annotation_layers

```sql
CREATE TABLE annotation_layers (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    canvas_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES image_sessions(id) ON DELETE CASCADE
);
```

### Table: edit_operations

```sql
CREATE TABLE edit_operations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    operation_type TEXT NOT NULL CHECK(operation_type IN ('draw', 'text', 'shape', 'filter', 'crop', 'resize')),
    canvas_snapshot TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    position INTEGER NOT NULL CHECK(position >= 0 AND position < 50),
    FOREIGN KEY (session_id) REFERENCES image_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_session_position ON edit_operations(session_id, position);
```

### Table: session_history

```sql
CREATE TABLE session_history (
    id TEXT PRIMARY KEY,
    terminal_session_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    image_source_type TEXT NOT NULL CHECK(image_source_type IN ('file', 'clipboard', 'url')),
    thumbnail_path TEXT,
    last_viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    view_count INTEGER NOT NULL DEFAULT 1,
    is_edited BOOLEAN NOT NULL DEFAULT 0,
    UNIQUE(terminal_session_id, image_path)
);

CREATE INDEX idx_terminal_last_viewed ON session_history(terminal_session_id, last_viewed_at DESC);
```

---

## Migration Strategy

Since this is a new feature, no migrations of existing data are required.

**Database Setup**:
1. Add new tables via Alembic migration
2. Tables are independent of existing jterm tables
3. No foreign keys to existing terminal session tables (loose coupling via terminal_session_id string)

**Cleanup Jobs**:
1. Delete `image_sessions` older than 24 hours
2. Delete `session_history` entries older than 7 days
3. Delete orphaned temporary files from `temp_file_path`

**Rollback Plan**:
If feature needs to be removed:
1. Drop tables: `edit_operations`, `annotation_layers`, `image_sessions`, `session_history`
2. Remove temporary file directories
3. No impact on existing jterm functionality

---

## Data Size Estimates

**Typical Session**:
- ImageSession: ~500 bytes
- AnnotationLayer: ~50KB (moderate annotations)
- EditOperations: 50 × 50KB = 2.5MB (full undo stack)
- SessionHistory: 20 × 200 bytes = 4KB

**Total per active session**: ~2.5-3MB

**Cleanup Strategy**:
- Active sessions: Kept in memory + SQLite
- Inactive sessions (>1 hour): SQLite only
- Old sessions (>24 hours): Deleted
- History entries (>7 days): Deleted

---

## Performance Considerations

**Indexing**:
- All foreign keys indexed
- Composite index on (session_id, position) for fast undo/redo
- Index on terminal_session_id for history queries

**Query Optimization**:
- Use prepared statements for all queries
- Limit session_history queries to 20 entries (LIMIT clause)
- Lazy-load canvas_json (don't fetch unless needed)

**Memory Management**:
- Keep active session in memory (Python dict)
- Serialize to SQLite on browser refresh or periodic backup
- Circular buffer for undo/redo (fixed 50-operation size)

**Concurrency**:
- Single user per terminal session (no concurrent editing)
- Optimistic locking via `version` field in annotation_layers
- File locks on temp_file_path during save operations

---

## Security Considerations

**Path Validation**:
- Sanitize `image_source_path` to prevent directory traversal
- Validate file extensions match `image_format`
- Use absolute paths for `temp_file_path`

**Data Privacy**:
- Temporary files stored in isolated session directories
- Cleanup on session close
- No persistent storage of clipboard images (deleted after session)

**Input Validation**:
- All fields validated against constraints on insert/update
- JSON fields validated as parseable before storage
- Enum fields restricted to allowed values via CHECK constraints

**SQL Injection Prevention**:
- Use parameterized queries (SQLite via aiosqlite)
- Never concatenate user input into SQL strings
- Validate UUIDs before using in queries
