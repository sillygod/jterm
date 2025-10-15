# Data Model: Enhanced Media Support and Performance Optimization

**Feature**: 002-enhance-and-implement
**Date**: 2025-10-09
**Status**: Design Complete

## Overview

This document defines the data models for three feature enhancements:
1. Ebook viewing (PDF/EPUB files)
2. Performance metrics monitoring
3. User preferences for metrics display

## Entity Relationship Diagram

```
UserProfile (existing)
    ↓ (1:N)
EbookMetadata
    - stores file metadata and cache info

TerminalSession (existing)
    ↓ (1:N)
PerformanceSnapshot
    - time-series performance data

UserProfile (extended)
    + show_performance_metrics: bool
    + performance_metric_refresh_interval: int
```

## Entity Definitions

### 1. EbookMetadata

Stores metadata and caching information for viewed PDF/EPUB files.

**Table**: `ebook_metadata`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| file_path | VARCHAR(512) | NOT NULL, INDEX | Absolute filesystem path |
| file_hash | VARCHAR(64) | UNIQUE, NOT NULL | SHA-256 hash for caching |
| file_type | ENUM('pdf', 'epub') | NOT NULL | File format |
| file_size | BIGINT | NOT NULL, CHECK(file_size <= 52428800) | Size in bytes (max 50MB) |
| title | VARCHAR(255) | NULLABLE | Extracted from metadata |
| author | VARCHAR(255) | NULLABLE | Extracted from metadata |
| total_pages | INTEGER | NULLABLE | For PDF only |
| is_encrypted | BOOLEAN | NOT NULL, DEFAULT FALSE | Password protection status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | First access time |
| last_accessed | TIMESTAMP | NOT NULL | Most recent access |
| user_id | UUID | FOREIGN KEY(user_profile.id) | Owner |

**Indexes**:
- PRIMARY: `id`
- INDEX: `file_path` (for quick lookup)
- UNIQUE: `file_hash` (deduplication)
- INDEX: `user_id` (for user queries)

**Validation Rules**:
- `file_size` MUST be ≤ 52428800 bytes (50MB limit)
- `file_type` MUST be one of ('pdf', 'epub')
- `file_path` MUST be absolute path and file must exist
- `file_hash` calculated as SHA-256 of file content
- `total_pages` required for PDF, NULL for EPUB
- `last_accessed` updated on each view

**Relationships**:
- **user** (N:1 to UserProfile): Owner of the ebook metadata

**State Transitions**: None (metadata record, no state machine)

### 2. PerformanceSnapshot

Time-series storage for performance metrics per terminal session.

**Table**: `performance_snapshots`

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| session_id | UUID | FOREIGN KEY(terminal_session.id), INDEX | Associated terminal session |
| timestamp | TIMESTAMP | NOT NULL, INDEX | Snapshot time |
| cpu_percent | FLOAT | NOT NULL, CHECK(cpu_percent >= 0 AND cpu_percent <= 100) | Server CPU % |
| memory_mb | FLOAT | NOT NULL, CHECK(memory_mb > 0) | Server memory MB |
| active_websockets | INTEGER | NOT NULL, CHECK(active_websockets >= 0) | Open WS connections |
| terminal_updates_per_sec | FLOAT | NOT NULL, DEFAULT 0 | Terminal write rate |
| client_fps | FLOAT | NULLABLE | Client-reported FPS |
| client_memory_mb | FLOAT | NULLABLE | Client JS heap MB |

**Indexes**:
- PRIMARY: `id`
- INDEX: `session_id, timestamp` (for time-series queries)
- INDEX: `timestamp` (for cleanup/retention)

**Validation Rules**:
- `cpu_percent` MUST be 0-100 range
- `memory_mb` MUST be positive
- `timestamp` MUST be within last hour (reject stale data)
- `active_websockets` MUST be non-negative
- Client metrics (`client_fps`, `client_memory_mb`) are optional

**Relationships**:
- **session** (N:1 to TerminalSession): Associated terminal session

**Retention Policy**:
- Snapshots older than 24 hours are deleted automatically
- Cleanup runs daily via scheduled task
- Users can export historical data via API before deletion

**State Transitions**: None (append-only, immutable snapshots)

### 3. UserProfile Extension

Extends existing `UserProfile` model with performance metrics preferences.

**Table**: `user_profile` (existing, add fields)

**New Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| show_performance_metrics | BOOLEAN | NOT NULL, DEFAULT FALSE | Toggle metrics display |
| performance_metric_refresh_interval | INTEGER | NOT NULL, DEFAULT 5000, CHECK(>= 1000 AND <= 60000) | Refresh interval (ms) |

**Validation Rules**:
- `performance_metric_refresh_interval` MUST be 1000-60000 milliseconds (1-60 seconds)
- Default is 5000ms (5 seconds) for balance between freshness and overhead

## Database Schema Changes

### Migration Script
**File**: `migrations/versions/2025_10_09_enhance_media_perf.py`

```python
"""enhance media support and performance optimization

Revision ID: 2025_10_09_0200
Revises: 2025_09_30_0115
Create Date: 2025-10-09
"""
from alembic import op
import sqlalchemy as sa

revision = '2025_10_09_0200'
down_revision = '2025_09_30_0115'

def upgrade():
    # Create ebook_metadata table
    op.create_table(
        'ebook_metadata',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('file_path', sa.String(512), nullable=False, index=True),
        sa.Column('file_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('file_type', sa.Enum('pdf', 'epub'), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('total_pages', sa.Integer, nullable=True),
        sa.Column('is_encrypted', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('last_accessed', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user_profile.id'), nullable=False),
        sa.CheckConstraint('file_size <= 52428800', name='file_size_limit')
    )
    op.create_index('idx_ebook_user', 'ebook_metadata', ['user_id'])

    # Create performance_snapshots table
    op.create_table(
        'performance_snapshots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(36), sa.ForeignKey('terminal_session.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False, index=True),
        sa.Column('cpu_percent', sa.Float, nullable=False),
        sa.Column('memory_mb', sa.Float, nullable=False),
        sa.Column('active_websockets', sa.Integer, nullable=False),
        sa.Column('terminal_updates_per_sec', sa.Float, nullable=False, default=0),
        sa.Column('client_fps', sa.Float, nullable=True),
        sa.Column('client_memory_mb', sa.Float, nullable=True),
        sa.CheckConstraint('cpu_percent >= 0 AND cpu_percent <= 100', name='cpu_range'),
        sa.CheckConstraint('memory_mb > 0', name='memory_positive')
    )
    op.create_index('idx_perf_session_time', 'performance_snapshots', ['session_id', 'timestamp'])

    # Extend user_profile table
    op.add_column('user_profile',
        sa.Column('show_performance_metrics', sa.Boolean, nullable=False, server_default='0'))
    op.add_column('user_profile',
        sa.Column('performance_metric_refresh_interval', sa.Integer, nullable=False, server_default='5000'))

def downgrade():
    op.drop_table('performance_snapshots')
    op.drop_table('ebook_metadata')
    op.drop_column('user_profile', 'performance_metric_refresh_interval')
    op.drop_column('user_profile', 'show_performance_metrics')
```

---

**Last Updated**: 2025-10-09
**Status**: Ready for implementation
