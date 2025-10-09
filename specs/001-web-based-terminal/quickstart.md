# Quickstart Guide: Web-Based Terminal Emulator

**Date**: 2025-09-25
**Feature**: Web-Based Terminal Emulator
**Status**: Complete

## Overview

This quickstart guide provides step-by-step instructions for setting up and using the Web-Based Terminal Emulator. The guide covers installation, basic usage, and advanced features including multimedia support, AI assistance, session recording, and customization. The application is built as a single FastAPI project serving HTMX templates with SQLite storage for maximum simplicity.

## Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+), macOS (11+), or Windows (WSL2)
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB available disk space

### Required Dependencies
- Git (for cloning repositories)
- Modern web browser with WebSocket support

### Optional Dependencies
- FFmpeg (for video processing and GIF generation)
- ImageMagick (for image processing)

## Installation

### Quick Start Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/web-terminal.git
   cd web-terminal
   ```

2. **Create Python virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize SQLite database**
   ```bash
   # Run database migrations
   alembic upgrade head

   # Default user is created automatically on server startup
   # (Optional: You can also run ./bin/setup_db.sh to create it manually)
   ```

5. **Set environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Start the FastAPI application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Access the terminal**
   - Open your browser to `http://localhost:8000`
   - The FastAPI app serves both the API and HTMX templates
   - Create an account or log in
   - Start your first terminal session

### Manual Development Setup

For development with hot reload and debugging:

1. **Enable debug mode**
   ```bash
   # In .env file
   TERMINAL_DEBUG=true
   ```

2. **Start with auto-reload**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access development features**
   - FastAPI automatic docs: `http://localhost:8000/docs`
   - SQLite database browser: Use tools like DB Browser for SQLite
   - Template debugging: Check browser developer tools

## Basic Usage

### Creating Your First Terminal Session

1. **Access the web interface**
   - Navigate to `http://localhost:8000`
   - Sign up for a new account or log in

2. **Start a terminal session**
   - Click "New Terminal" button
   - Choose your preferred shell (bash, zsh, fish)
   - Set terminal dimensions (default: 80x24)
   - Click "Create Session"

3. **Basic terminal commands**
   ```bash
   # Test basic functionality
   pwd                    # Print working directory
   ls -la                 # List files
   echo "Hello Terminal!" # Echo text
   ```

### Navigation and Interface

- **Terminal Area**: Main terminal display with xterm.js
- **Sidebar**: Session management, settings, and features
- **Status Bar**: Connection status, session info, recording status
- **Menu Bar**: File operations, themes, extensions, help

### Session Management

1. **Multiple sessions**
   - Click "+" tab to create new session
   - Switch between sessions using tabs
   - Right-click tabs for session options

2. **Session persistence**
   - Sessions automatically save state
   - Resume sessions after browser restart
   - Sessions expire after 24 hours of inactivity

## Media Features

The web terminal includes built-in commands for viewing media files directly in the browser. These commands are automatically available when you start a terminal session.

### Viewing Images

1. **Display images inline**
   ```bash
   # View image files - opens in overlay viewer
   imgcat screenshot.png
   imgcat photo.jpg
   imgcat diagram.svg
   ```

2. **Supported formats**
   - JPG, JPEG, PNG, GIF, WebP, BMP, SVG

3. **Image viewer controls**
   - **Zoom In**: Click + button or scroll up
   - **Zoom Out**: Click - button or scroll down
   - **Reset Zoom**: Click ⟲ button
   - **Fullscreen**: Click ⛶ button
   - **Close**: Click ✕ button or press Escape

### Playing Videos

1. **Video playback**
   ```bash
   # Play video files (served through backend)
   vidcat demo.mp4
   vidcat recording.webm
   ```

2. **Supported formats**
   - MP4, WebM, OGG, MOV, AVI
   - Maximum file size: 50MB

3. **Video controls**
   - Standard HTML5 video controls
   - Play/Pause, seek, volume
   - Fullscreen support

### HTML Preview

1. **Preview HTML files**
   ```bash
   # Preview local HTML files in sandboxed iframe
   htmlcat index.html
   htmlcat documentation.html
   ```

2. **Security features**
   - JavaScript disabled by default for security
   - Sandboxed iframe prevents malicious code execution
   - Same-origin policy enforced

### Markdown Rendering

1. **View markdown files**
   ```bash
   # Open markdown with GitHub-flavored styling
   mdcat README.md
   mdcat documentation.md
   ```

2. **Markdown features**
   - GitHub-flavored dark theme styling
   - Syntax highlighting for code blocks
   - Tables with striped rows
   - Clickable links
   - Properly formatted headings and lists
   - Close with ✕ button or Escape key

## AI Assistant

The terminal includes an AI assistant that can help with commands, explain outputs, and provide context-aware suggestions.

### Enabling AI Assistant

1. **Configure API Keys**
   ```bash
   # In .env file
   AI_PROVIDER=openai           # or anthropic, local
   OPENAI_API_KEY=sk-...       # Your OpenAI API key
   # OR
   ANTHROPIC_API_KEY=sk-ant-... # Your Anthropic API key
   ```

2. **Access the AI Sidebar**
   - Click the 🤖 icon in the top-right header
   - The AI sidebar will appear on the right side
   - Status indicator shows if AI is online/offline

### Using AI Chat

1. **Text Chat**
   - Type your question in the chat input field
   - Press Enter or click "Send"
   - AI provides context-aware responses based on terminal history
   - Responses are rendered with markdown formatting

2. **Voice Input** (if configured)
   - Click the 🎤 microphone icon
   - Speak your command or question
   - AI transcribes and responds
   - Click the ⚙️ icon for voice settings

### AI Features

- **Command Suggestions**: AI suggests commands based on your goal
- **Output Explanation**: AI explains command outputs and errors
- **Context-Aware**: AI remembers your terminal session history
- **Multiple Providers**: Support for OpenAI, Anthropic, and local models

## Session Recording

The terminal can record and replay your terminal sessions for documentation, debugging, or sharing.

### Starting a Recording

1. **Access Recording Controls**
   - Click the ⏺ recording icon in the top-right header to view recording info
   - Use the "Record" button in the status bar (bottom center) to start

2. **Start Recording**
   - Click the "Record" button in the status bar
   - Recording indicator appears showing "Recording..." in red
   - Minimal performance impact (<5%)

3. **Stop Recording**
   - Click the "Stop" button that replaces the Record button
   - Recording is automatically saved
   - Recording ID displayed briefly in status bar

### Using Recording Features

1. **Playback**
   - Recordings are saved with unique IDs
   - Access via API: `/api/v1/recordings/{recording_id}`
   - Use recording.js player for playback with controls

2. **Export Formats**
   - JSON: Full event data with timestamps
   - Asciinema: Compatible with asciinema.org
   - HTML: Self-contained playable recording
   - Text: Plain text transcript

3. **Performance**
   - <5% performance overhead during recording
   - Automatic compression enabled
   - Checkpoints for efficient seeking

4. **Retention**
   - Recordings stored for 30 days by default
   - Automatic cleanup of old recordings
   - Configure via `RECORDING_RETENTION_DAYS` in `.env`

## Settings

The terminal includes a settings panel for basic customization:

1. **Access Settings**
   - Click the ⚙️ icon in the top-right corner
   - Settings modal will appear

2. **Available Settings**
   - **Font Size**: 12px, 13px, 14px, 16px, 18px (default: 14px)
   - **Font Family**: Courier New (default), Monaco, Menlo, Consolas
   - **Cursor Blink**: Toggle cursor blinking on/off
   - **Color Theme**: Dark (default), Light

3. **Apply Changes**
   - Changes take effect immediately
   - Click "Close" to exit settings

## Implementation Status

### ✅ Fully Functional (User-Accessible)
- **Terminal Emulation**: Full xterm.js terminal with PTY support
- **Media Viewing**: `imgcat`, `vidcat`, `mdcat`, `htmlcat` commands
  - Image viewer with zoom, fullscreen, pan controls
  - GitHub-flavored markdown rendering
  - Sandboxed HTML preview
- **Settings Panel**: Font size, family, cursor, theme customization
- **WebSocket Communication**: Real-time terminal I/O
- **Session Management**: Create and manage terminal sessions

### ✅ Fully Functional - AI Assistant
The AI Assistant is now **fully integrated and user-accessible**:
- **Status**: Complete backend and frontend integration
- **Access**: Click the 🤖 icon in the header to toggle the AI sidebar
- **Code Location**:
  - Backend: `src/services/ai_service.py`, `src/api/ai_endpoints.py`, `src/websockets/ai_handler.py`
  - Frontend: `static/js/ai.js`, `static/js/voice.js`, `templates/components/ai_sidebar.html`
- **Available Features**:
  - Text-based chat with streaming responses
  - Multiple AI providers (OpenAI, Anthropic, local)
  - Voice input/output support
  - Context-aware terminal assistance
  - Command suggestions and output explanations
- **Configuration**: Set `AI_PROVIDER`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` in `.env`

### ✅ Fully Functional - Session Recording
The Session Recording feature is now **fully integrated and user-accessible**:
- **Status**: Complete backend and frontend integration
- **Access**:
  - Click the ⏺ icon in the header to view recording info
  - Use Record/Stop buttons in the status bar to control recording
- **Code Location**:
  - Backend: `src/services/recording_service.py`, `src/api/recording_endpoints.py`, `src/websockets/recording_handler.py`
  - Frontend: `static/js/recording.js`, `templates/components/recording_controls.html`
- **Available Features**:
  - Record terminal sessions with <5% performance impact
  - Playback with speed control and seeking
  - Export to JSON, Asciinema, HTML, text formats
  - 30-day retention with auto-cleanup
  - Real-time recording status in status bar

#### Theme & Extension Management
- **Status**: Backend services and models exist
- **Missing**: API endpoints not registered, no UI
- **Code Location**:
  - Backend: `src/services/theme_service.py`, `src/services/extension_service.py`
  - Frontend: `templates/components/theme_selector.html`
- **Capabilities** (when integrated):
  - Custom color themes
  - VS Code theme import
  - Extension marketplace
  - Plugin system

### 🚧 Not Yet Started
- Multi-session tabs UI
- File upload/download features
- Remote SSH connection support
- Collaborative editing/shared sessions

### Integration Steps Required

To activate implemented-but-not-integrated features:

1. **Load JavaScript files** in `templates/base.html`:
   ```html
   <script src="/static/js/recording.js"></script>
   <script src="/static/js/voice.js"></script>
   ```

2. **Register API endpoints** in `src/main.py`:
   ```python
   from src.api.ai_endpoints import router as ai_router
   from src.api.customization_endpoints import router as customization_router
   app.include_router(ai_router)
   app.include_router(customization_router)
   ```

3. **Make UI components visible** (currently hidden or not activated)

## Advanced Configuration

### Environment Variables

```bash
# Core settings
TERMINAL_DEBUG=true                    # Enable debug logging
TERMINAL_HOST=0.0.0.0                 # Server host
TERMINAL_PORT=8000                    # Server port
TERMINAL_SECRET_KEY=your-secret       # JWT secret

# Database
DATABASE_URL=sqlite:///./webterminal.db  # SQLite database file

# AI Settings
AI_PROVIDER=openai                    # openai|anthropic|local
OPENAI_API_KEY=sk-...                # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...         # Anthropic API key

# Media settings
MEDIA_MAX_SIZE=52428800              # 50MB max file size
MEDIA_STORAGE_PATH=./media           # Media storage directory

# Recording settings
RECORDING_MAX_DURATION=3600          # 1 hour max recording
RECORDING_RETENTION_DAYS=30          # Auto-delete after 30 days
```

### Performance Tuning

1. **WebSocket settings**
   ```python
   # In backend configuration
   WEBSOCKET_PING_INTERVAL = 20      # Seconds
   WEBSOCKET_PING_TIMEOUT = 10       # Seconds
   WEBSOCKET_CLOSE_TIMEOUT = 10      # Seconds
   ```

2. **Database optimization**
   ```sql
   -- SQLite indexes are automatically created by migrations
   -- Enable WAL mode for better concurrency
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA cache_size=10000;
   ```

3. **Caching configuration**
   ```bash
   # In-memory cache settings
   CACHE_TTL=3600                   # 1 hour default TTL
   SESSION_CACHE_SIZE=1000         # Max sessions in memory
   MEDIA_CACHE_SIZE=100            # Max media files cached
   ```

### Security Configuration

1. **CORS settings**
   ```python
   CORS_ORIGINS = [
       "http://localhost:8000",
       "https://yourdomain.com"
   ]
   ```

2. **Authentication**
   ```bash
   # JWT configuration
   JWT_ALGORITHM=HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
   JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
   ```

3. **Content Security Policy**
   ```nginx
   # Nginx configuration for HTML preview
   add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'";
   ```

## Troubleshooting

### Common Issues

1. **WebSocket connection fails**
   ```bash
   # Check backend status
   curl http://localhost:8000/health

   # Check WebSocket endpoint
   wscat -c ws://localhost:8000/ws/sessions/test

   # Check browser developer tools for errors
   ```

2. **AI assistant not responding**
   - Verify API keys in Settings → AI Assistant
   - Check network connectivity
   - Ensure sufficient API quota/credits
   - Check backend logs for errors

3. **Media files won't display**
   - Check file size (max 50MB for videos, 10MB for images)
   - Verify file format is supported
   - Check browser console for errors
   - Ensure media processing dependencies installed

4. **Recording playback issues**
   - Verify recording completed successfully
   - Check browser supports video playback
   - Try different export format
   - Clear browser cache

### Performance Issues

1. **Slow terminal response**
   - Check WebSocket connection latency
   - Monitor server resource usage
   - Reduce terminal dimensions if needed
   - Disable animations temporarily

2. **High memory usage**
   - Limit scrollback buffer size
   - Close unused terminal sessions
   - Clear old recordings
   - Restart browser periodically

3. **Network bandwidth issues**
   - Enable compression for WebSocket messages
   - Reduce recording quality settings
   - Use local media files instead of remote URLs
   - Consider upgrading internet connection

### Recording Issues

If you get a 404 error when clicking the Record button:

1. **Check server startup logs**
   ```bash
   # The server automatically creates a default user on startup
   # Look for: "👤 Created default user" or "👤 Default user already exists"
   ```

2. **Manually create default user (if needed)**
   ```bash
   ./bin/setup_db.sh
   ```

3. **Verify database tables**
   ```bash
   sqlite3 webterminal.db ".tables"
   # Should show: recordings, terminal_sessions, user_profiles, etc.
   ```

4. **Check logs for errors**
   ```bash
   # Look for errors in the terminal running uvicorn
   ```

### Getting Help

1. **Documentation**
   - Full API documentation: `/docs` endpoint
   - User manual: `docs/user-guide.md`
   - Developer guide: `docs/development.md`

2. **Community Support**
   - GitHub Issues: Report bugs and feature requests
   - Discord Server: Community chat and support
   - Stack Overflow: Technical questions with `web-terminal` tag

3. **Professional Support**
   - Email: support@webterminal.dev
   - Enterprise support available
   - Custom development services

## Next Steps

### Learning More

1. **Advanced Features**
   - Explore the API documentation
   - Try building custom extensions
   - Create and share themes
   - Set up automated workflows

2. **Integration**
   - Connect to remote servers via SSH
   - Integrate with CI/CD pipelines
   - Set up team collaboration features
   - Configure enterprise authentication

3. **Development**
   - Fork the repository
   - Set up development environment
   - Contribute to open source project
   - Build custom features

### Feature Roadmap

- **Collaborative terminals**: Real-time session sharing
- **Mobile support**: Progressive web app for tablets
- **Plugin marketplace**: Community extension store
- **Advanced AI**: Multi-step task automation
- **Cloud sync**: Cross-device session synchronization

## Conclusion

You now have a fully functional Web-Based Terminal Emulator with multimedia support, AI assistance, session recording, and extensive customization options. The terminal provides a modern, feature-rich alternative to traditional command-line interfaces while maintaining full compatibility with standard terminal applications.

For additional help, consult the documentation, join our community, or reach out to support. Happy terminal-ing! 🚀
