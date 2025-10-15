# jterm - Web Terminal Emulator

A modern, web-based terminal emulator with multimedia support, AI assistance, and session recording capabilities. Built with FastAPI, xterm.js, and HTMX for a seamless terminal experience in your browser.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)

## Features

- **Full Terminal Emulation**: Real PTY integration with xterm.js providing a complete terminal experience
- **Multimedia Support**: View images, videos, and preview HTML files directly in the terminal
- **AI Assistant**: Context-aware AI assistance with voice input/output capabilities
- **Session Recording**: Record, replay, and export terminal sessions
- **Customization**: Themes, extensions, and VS Code theme import support
- **Markdown Rendering**: Beautiful GitHub-flavored markdown preview
- **Real-time Communication**: WebSocket-based terminal and AI interactions
- **Secure**: HTML sandboxing, file validation, and secure API communications

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Virtual environment (recommended)
- SQLite 3
- Optional: FFmpeg for video processing

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/jterm.git
   cd jterm
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

5. **Initialize database**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Open in browser**
   ```
   http://localhost:8000
   ```

## Configuration

### Essential Environment Variables

```bash
# Server
TERMINAL_HOST=0.0.0.0
TERMINAL_PORT=8000
TERMINAL_SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///./webterminal.db

# AI Provider (optional)
AI_PROVIDER=openai  # Options: openai, anthropic, local
OPENAI_API_KEY=your-api-key-here
```

See `.env.example` for all available configuration options.

### AI Assistant Setup

jterm supports multiple AI providers. For quick setup:

**Groq (Free & Fast)**
```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.groq.com/openai
LOCAL_AI_API_KEY=your-groq-api-key
LOCAL_AI_MODEL=mixtral-8x7b-32768
```

**Ollama (Local & Free)**
```bash
# Install Ollama first: https://ollama.ai
ollama pull mistral

AI_PROVIDER=local
LOCAL_AI_ENDPOINT=http://localhost:11434
LOCAL_AI_MODEL=mistral
```

See [AI_SETUP_QUICKSTART.md](AI_SETUP_QUICKSTART.md) for detailed AI provider setup instructions.

## Project Structure

```
jterm/
├── src/
│   ├── api/              # REST API endpoints
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic (PTY, Media, AI, Recording)
│   ├── websockets/       # WebSocket handlers
│   ├── middleware/       # Auth, logging, security
│   ├── database/         # Database connection and migrations
│   └── main.py           # FastAPI application
├── templates/
│   ├── base.html         # Main HTMX template
│   ├── terminal.html     # Terminal interface
│   └── components/       # Reusable HTMX components
├── static/
│   ├── js/               # Frontend JavaScript
│   ├── css/              # Stylesheets
│   └── assets/           # Static assets
├── tests/
│   ├── contract/         # API contract tests
│   ├── integration/      # Integration tests
│   ├── unit/             # Unit tests
│   └── e2e/              # End-to-end tests
├── migrations/           # Alembic database migrations
└── specs/                # Feature specifications and plans
```

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Development Server

```bash
# With auto-reload
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# Debug mode
TERMINAL_DEBUG=true uvicorn src.main:app --reload
```

## Usage

### Terminal Operations

- **New Session**: The terminal automatically creates a session on connection
- **Keyboard Shortcuts**: Standard terminal shortcuts work (Ctrl+C, Ctrl+D, etc.)
- **Copy/Paste**: Use browser's standard copy/paste or right-click context menu

### Media Viewing

```bash
# View an image
imgcat image.png
# Or use the custom viewer command
imgcat image.jpg

# Play a video
vidcat video.mp4

# Preview HTML
htmlcat document.html

# Render markdown
mdcat README.md
```

### AI Assistant

1. Click the AI sidebar icon or press the configured hotkey
2. Type your question or click the microphone for voice input
3. Get context-aware suggestions and help
4. Ask for command explanations or debugging assistance

### Session Recording

- **Start Recording**: Click the record button in the toolbar
- **Stop Recording**: Click again to stop
- **Playback**: Access recordings from the sessions menu
- **Export**: Download recordings in various formats

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Key Endpoints

- `GET /` - Main terminal interface
- `WebSocket /ws/terminal` - Terminal communication
- `WebSocket /ws/ai` - AI assistant communication
- `POST /api/media/process` - Process media files
- `GET /api/recordings/{id}` - Retrieve session recordings

## Performance

- **Image Loading**: < 1 second
- **AI Responses**: < 2s (simple queries), < 5s (complex queries)
- **Recording Impact**: < 5% performance overhead
- **Video Support**: Up to 50MB files
- **Session Retention**: 30 days (configurable)

## Security

- HTML preview uses iframe sandboxing
- File type validation for uploads
- JWT-based authentication (planned)
- CORS protection
- Secure WebSocket connections
- Environment-based secrets management

## Troubleshooting

### Database Issues
```bash
# Reset database
rm webterminal.db
alembic upgrade head
```

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Use a different port
uvicorn src.main:app --port 8080
```

### AI Assistant Offline
- Verify API keys in `.env`
- Check endpoint URLs
- Review server logs for errors
- See [AI_SETUP_QUICKSTART.md](AI_SETUP_QUICKSTART.md)

### Orphan Processes
```bash
# Clean up orphan Python processes (macOS/Linux)
ps aux | grep "jterm/venv/bin/python3" | awk '{print $2}' | xargs kill -9
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Use type hints
- Run linters before committing

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

## Technology Stack

### Backend
- **FastAPI**: Modern, high-performance web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **SQLite**: Lightweight database
- **WebSockets**: Real-time bidirectional communication
- **Python PTY**: Terminal emulation

### Frontend
- **xterm.js**: Terminal emulator for the web
- **HTMX**: Modern web interactions
- **Hyperscript**: Client-side scripting
- **JavaScript ES2022**: Modern JavaScript features

### AI & Media
- **OpenAI/Anthropic/Local AI**: Multiple AI provider support
- **Pillow**: Image processing
- **FFmpeg**: Video processing
- **Markdown**: Document rendering

## Roadmap

- [ ] User authentication and authorization
- [ ] Multi-user sessions
- [ ] Terminal sharing and collaboration
- [ ] Plugin system
- [ ] Cloud storage integration
- [ ] Enhanced AI features (code completion, error analysis)
- [ ] Performance monitoring dashboard

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [xterm.js](https://xtermjs.org/) - Terminal emulation
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [HTMX](https://htmx.org/) - Modern web interactions
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit

## Support

- **Documentation**: See `/docs` directory
- **Issues**: [GitHub Issues](https://github.com/yourusername/jterm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/jterm/discussions)

## Authors

Built with care for developers who love the terminal.

---

**Note**: This project is under active development. Features and APIs may change.
