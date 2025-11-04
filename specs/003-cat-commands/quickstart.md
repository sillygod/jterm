# Quickstart Guide: Web-Enhanced Cat Commands

**Feature**: 003-cat-commands
**Branch**: `003-cat-commands`
**Date**: 2025-11-04

## Overview

This guide helps developers implement the four web-enhanced terminal commands (logcat, certcat, sqlcat, curlcat) following TDD principles and jterm architecture patterns.

## Prerequisites

```bash
# Verify Python version
python --version  # Should be 3.11+

# Activate virtual environment
cd /Users/jing/Downloads/mycrafts/jterm
source venv/bin/activate

# Install new dependencies
pip install httpx>=0.24.0
pip install aiosqlite>=0.19.0
pip install asyncpg>=0.28.0
pip install cryptography>=41.0.0
pip install python-dateutil>=2.8.0
pip install openpyxl>=3.1.0
pip install certifi>=2023.0.0

# Verify existing setup
pytest --version
black --version
flake8 --version
```

## Development Workflow

### 1. Test-First Development (TDD - MANDATORY)

jterm follows strict TDD: **Write tests → Get approval → Tests fail → Implement → Tests pass**

**DO NOT implement features before writing tests.** This is non-negotiable per CLAUDE.md guidelines.

#### Test Structure

```bash
tests/
├── unit/                # Business logic tests (write FIRST)
│   ├── test_log_service.py
│   ├── test_cert_service.py
│   ├── test_sql_service.py
│   └── test_http_service.py
│
├── contract/            # API contract tests (write SECOND)
│   ├── test_log_api.py
│   ├── test_cert_api.py
│   ├── test_sql_api.py
│   └── test_http_api.py
│
├── integration/         # End-to-end user story tests (write THIRD)
│   ├── test_logcat_flow.py
│   ├── test_certcat_flow.py
│   ├── test_sqlcat_flow.py
│   └── test_curlcat_flow.py
│
└── e2e/                # UI tests (write LAST)
    ├── test_log_viewer_ui.py
    ├── test_cert_viewer_ui.py
    ├── test_sql_viewer_ui.py
    └── test_curl_viewer_ui.py
```

#### Example Test Cycle (LOGCAT)

**Step 1: Write Unit Test**
```python
# tests/unit/test_log_service.py
import pytest
from src.services.log_service import LogService
from src.models.log_entry import LogEntry, LogFormat

@pytest.mark.asyncio
async def test_parse_json_log():
    """Test parsing JSON log format"""
    service = LogService()
    log_line = '{"timestamp": "2025-11-04T10:00:00Z", "level": "ERROR", "message": "Test error"}'

    entry = await service.parse_line(log_line, LogFormat.JSON, line_number=1)

    assert entry.level == LogLevel.ERROR
    assert entry.message == "Test error"
    assert entry.line_number == 1
    assert "timestamp" in entry.structured_fields
```

**Step 2: Run Test (should FAIL)**
```bash
pytest tests/unit/test_log_service.py::test_parse_json_log -v
# Expected: FAIL (log_service.py doesn't exist yet)
```

**Step 3: Implement ONLY Enough to Pass**
```python
# src/services/log_service.py
import json
from src.models.log_entry import LogEntry, LogFormat, LogLevel
from datetime import datetime

class LogService:
    async def parse_line(self, line: str, format: LogFormat, line_number: int) -> LogEntry:
        if format == LogFormat.JSON:
            data = json.loads(line)
            return LogEntry(
                timestamp=datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00")),
                level=LogLevel[data["level"]],
                message=data["message"],
                line_number=line_number,
                raw_text=line,
                structured_fields=data
            )
        # TODO: Other formats later
        raise NotImplementedError(f"Format {format} not yet implemented")
```

**Step 4: Run Test Again (should PASS)**
```bash
pytest tests/unit/test_log_service.py::test_parse_json_log -v
# Expected: PASS
```

**Step 5: Refactor & Repeat**
Continue cycle for each feature/requirement.

### 2. Implementation Order (By Priority)

Follow spec priorities (P1 → P2 → P3):

#### Phase 1: LOGCAT (P1 - Highest Priority)
1. **Models** (`src/models/log_entry.py`)
   - LogEntry dataclass
   - LogFilter dataclass
   - LogLevel enum
   - LogFormat enum

2. **Service** (`src/services/log_service.py`)
   - `parse_line()` - Parse single log line
   - `parse_file()` - Parse entire file
   - `detect_format()` - Auto-detect log format
   - `filter_entries()` - Apply filters
   - `stream_file()` - Real-time streaming (async generator)

3. **API** (`src/api/log_endpoints.py`)
   - `POST /api/logs/parse`
   - `POST /api/logs/filter`
   - `GET /api/logs/stream` (WebSocket)
   - `POST /api/logs/export`

4. **Bash Command** (`bin/logcat`)
   - Argument parsing
   - OSC sequence output

5. **Frontend** (`static/js/log-viewer.js`, `templates/components/log_viewer.html`)
   - LogViewer class
   - Split-view UI
   - Filter sidebar
   - Search with regex

6. **Tests** (all layers)

#### Phase 2: CERTCAT + SQLCAT (P2 - Equal Priority)
Implement both in parallel or sequentially. Same structure as LOGCAT.

#### Phase 3: CURLCAT (P3 - Lowest Priority)
Implement last. Same structure as LOGCAT.

### 3. File Creation Template

For each new file, follow this template:

```python
# src/services/example_service.py
"""
Service description.

Handles: [List main responsibilities]
Dependencies: [List dependencies]
"""

from typing import List, Optional
from dataclasses import dataclass

# Import models
from src.models.example import ExampleModel


class ExampleService:
    """
    Service class description.

    Public methods:
    - method_name(): Description
    """

    def __init__(self):
        """Initialize service"""
        pass

    async def example_method(self, param: str) -> ExampleModel:
        """
        Method description.

        Args:
            param: Parameter description

        Returns:
            ExampleModel: Return value description

        Raises:
            ValueError: When validation fails
        """
        # Implementation
        pass
```

### 4. Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_log_service.py -v

# Run specific test function
pytest tests/unit/test_log_service.py::test_parse_json_log -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v
```

### 5. Code Quality Checks

```bash
# Format code (run before committing)
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# All checks together
black src/ tests/ && flake8 src/ tests/ && mypy src/ && pytest
```

### 6. Adding New API Endpoints

**Step 1: Define in `src/api/example_endpoints.py`**
```python
from fastapi import APIRouter, HTTPException
from src.services.example_service import ExampleService
from src.models.example import ExampleRequest, ExampleResponse

router = APIRouter(prefix="/api/example", tags=["example"])
service = ExampleService()

@router.post("/action")
async def perform_action(request: ExampleRequest) -> ExampleResponse:
    """Endpoint description"""
    try:
        result = await service.perform_action(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Step 2: Register in `src/main.py`**
```python
from src.api import log_endpoints, cert_endpoints, sql_endpoints, http_endpoints

app.include_router(log_endpoints.router)
app.include_router(cert_endpoints.router)
app.include_router(sql_endpoints.router)
app.include_router(http_endpoints.router)
```

### 7. Adding OSC Sequence Handler

**Step 1: Create bash command** (`bin/logcat`)
```bash
#!/bin/bash
# Usage: logcat <file>

FILE_PATH="$1"
ABS_PATH=$(realpath "$FILE_PATH")

# Send OSC 1337 sequence
printf '\033]1337;ViewLog=%s\007' "$ABS_PATH"
```

**Step 2: Register handler in** `static/js/terminal.js`
```javascript
// In setupEventListeners() method
this.terminal.parser.registerOscHandler(1337, (data) => {
    const [command, params] = data.split('=');

    switch(command) {
        case 'ViewLog':
            window.logViewer.open(params);
            break;
        case 'ViewCert':
            window.certViewer.open(params);
            break;
        case 'QuerySQL':
            window.sqlViewer.open(params);
            break;
        case 'HTTPRequest':
            window.curlViewer.open(params);
            break;
        // ... existing cases (ViewImage, ViewVideo, ViewEbook)
    }

    return true;
});
```

### 8. Frontend Development

**JavaScript Module Pattern** (follow existing bookcat/imgcat pattern):

```javascript
// static/js/log-viewer.js
class LogViewer {
    constructor() {
        this.container = document.getElementById('log-viewer-container');
        this.isOpen = false;
        this.entries = [];
        this.filter = {};
    }

    async open(filePath) {
        // Fetch log data from API
        const response = await fetch('/api/logs/parse', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file_path: filePath})
        });

        const data = await response.json();
        this.entries = data.entries;

        // Render UI
        this.render();
        this.show();
    }

    render() {
        // Use HTMX for dynamic updates
        htmx.ajax('GET', '/components/log_viewer', {
            target: '#log-viewer-container',
            swap: 'innerHTML'
        });
    }

    show() {
        this.container.classList.add('visible');
        this.isOpen = true;
    }

    close() {
        this.container.classList.remove('visible');
        this.isOpen = false;
    }
}

// Initialize on page load
window.logViewer = new LogViewer();
```

**HTMX Template** (`templates/components/log_viewer.html`):
```html
<div id="log-viewer-container" class="viewer-overlay">
    <div class="viewer-header">
        <h2>Log Viewer: {{ file_name }}</h2>
        <button onclick="window.logViewer.close()">Close</button>
    </div>

    <div class="viewer-content split-view">
        <!-- Left: Log list -->
        <div class="log-list">
            {% for entry in entries %}
            <div class="log-entry level-{{ entry.level }}"
                 onclick="showLogDetail('{{ entry.line_number }}')">
                <span class="timestamp">{{ entry.display_time }}</span>
                <span class="level">{{ entry.level }}</span>
                <span class="message">{{ entry.message }}</span>
            </div>
            {% endfor %}
        </div>

        <!-- Right: Detail panel -->
        <div class="log-detail" id="log-detail-panel">
            <p>Select a log entry to view details</p>
        </div>
    </div>
</div>
```

### 9. Debugging Tips

**Backend Debugging**:
```python
# Add logging
import logging
logger = logging.getLogger(__name__)

async def example_method(self):
    logger.info("Starting example_method")
    logger.debug(f"Processing with params: {params}")
    # ...
```

**Frontend Debugging**:
```javascript
// Use console.log liberally
console.log('LogViewer.open() called with:', filePath);

// Inspect WebSocket messages
this.websocket.onmessage = (event) => {
    console.log('WebSocket message received:', event.data);
    // ...
};
```

**Network Debugging**:
```bash
# Test API endpoints directly
curl -X POST http://localhost:8000/api/logs/parse \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/var/log/test.log"}'
```

### 10. Performance Optimization

Follow these patterns to maintain <5% CPU idle:

```python
# ✓ GOOD: Async file reading with batching
async def parse_file(self, path: str, batch_size: int = 1000):
    async with aiofiles.open(path, 'r') as f:
        batch = []
        async for line in f:
            batch.append(line)
            if len(batch) >= batch_size:
                yield await self.parse_batch(batch)
                batch = []

# ✗ BAD: Sync file reading, loads entire file
def parse_file(self, path: str):
    with open(path, 'r') as f:
        return [self.parse_line(line) for line in f.readlines()]
```

### 11. Common Patterns

**Error Handling**:
```python
try:
    result = await service.dangerous_operation()
except FileNotFoundError:
    raise HTTPException(status_code=404, detail="File not found")
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Validation**:
```python
def __post_init__(self):
    """Validate dataclass fields"""
    if not self.url.startswith(('http://', 'https://')):
        raise ValueError(f"Invalid URL: {self.url}")
```

**Async Context Managers**:
```python
async with aiosqlite.connect(db_path) as conn:
    async with conn.execute(query) as cursor:
        result = await cursor.fetchall()
```

### 12. Git Workflow

```bash
# Check current branch
git branch --show-current  # Should be 003-cat-commands

# Commit frequently (small, atomic commits)
git add src/models/log_entry.py tests/unit/test_log_service.py
git commit -m "Add LogEntry model with validation tests"

# Push to remote (when ready)
git push -u origin 003-cat-commands
```

### 13. Documentation

**Code Comments** (use docstrings):
```python
def parse_apache_log(self, line: str) -> LogEntry:
    """
    Parse Apache Combined Log Format.

    Format: IP - - [timestamp] "method path protocol" status size "referer" "user-agent"
    Example: 192.168.1.1 - - [04/Nov/2025:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234 "..." "..."

    Args:
        line: Raw log line string

    Returns:
        LogEntry: Parsed log entry

    Raises:
        ValueError: If line doesn't match Apache format
    """
```

### 14. Running the Application

```bash
# Start development server (with auto-reload)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Access terminal
open http://localhost:8000

# Test commands in terminal
logcat /var/log/app.log
certcat https://example.com
sqlcat --db test.db --query "SELECT * FROM users"
curlcat https://api.github.com/users/octocat
```

## Troubleshooting

### Common Issues

**Issue**: Import errors (`ModuleNotFoundError`)
**Solution**: Ensure you're in the venv: `source venv/bin/activate`

**Issue**: Tests fail with `RuntimeError: Event loop is closed`
**Solution**: Use `@pytest.mark.asyncio` decorator on async tests

**Issue**: WebSocket connection fails
**Solution**: Check that server is running and port 8000 is not blocked

**Issue**: OSC sequence not triggering viewer
**Solution**: Check terminal.js for correct handler registration (OSC 1337)

### Getting Help

1. Check CLAUDE.md for project conventions
2. Review existing implementations (bookcat, imgcat, vidcat)
3. Read API contracts in `specs/003-cat-commands/contracts/`
4. Consult research.md for technology decisions

## Next Steps

After completing this feature:

1. **Run full test suite**: `pytest`
2. **Check coverage**: `pytest --cov=src --cov-report=html`
3. **Update CLAUDE.md**: Add new commands to Key Features section
4. **Create PR**: Follow git commit message format with Claude Co-Author
5. **Demo**: Test all four commands end-to-end

## Resources

- **Spec**: `specs/003-cat-commands/spec.md`
- **Research**: `specs/003-cat-commands/research.md`
- **Data Models**: `specs/003-cat-commands/data-model.md`
- **API Contracts**: `specs/003-cat-commands/contracts/api-contracts.yaml`
- **jterm Guidelines**: `CLAUDE.md`

Happy coding! Remember: **Tests first, implementation second.** 🧪
