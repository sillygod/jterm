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
3. **AI Assistant**: Voice input/output, context-aware suggestions (2s simple, 5s complex responses)
4. **Session Recording**: Record/replay/export with 30-day retention, <5% performance impact
5. **Customization**: Themes, extensions, VS Code theme import
6. **Security**: HTML sandboxing, file validation, secure API communications

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
- Image loading: <1 second
- AI responses: <2s simple, <5s complex
- Session recording impact: <5% performance degradation
- Video file limit: 50MB maximum

## Recent Changes
- 001-web-based-terminal: Initial feature specification and implementation plan

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->