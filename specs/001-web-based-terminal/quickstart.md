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
   # Database is automatically created on first run
   # Run migrations if needed
   alembic upgrade head
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
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

### Viewing Images

1. **Display images inline**
   ```bash
   # View image files
   view screenshot.png
   view photo.jpg
   view diagram.gif
   ```

2. **Remote images**
   ```bash
   # View images from URLs
   view https://example.com/image.png
   ```

3. **Image controls**
   - **Zoom**: Scroll wheel or +/- keys
   - **Pan**: Click and drag
   - **Full screen**: Double-click image
   - **Info**: Press 'i' for image details

### Playing Videos

1. **Video playback**
   ```bash
   # Play video files (up to 50MB)
   play demo.mp4
   play recording.webm
   ```

2. **Video controls**
   - **Play/Pause**: Spacebar or click play button
   - **Seek**: Arrow keys or progress bar
   - **Volume**: Up/Down arrows or volume slider
   - **Full screen**: 'f' key or full screen button

### HTML Preview

1. **Preview HTML files**
   ```bash
   # Preview local HTML files
   htmlview index.html
   htmlview documentation.html
   ```

2. **Security settings**
   - JavaScript disabled by default
   - Enable JS with: `htmlview --allow-js index.html`
   - Sandboxed iframe with CSP protection

### Markdown Rendering

1. **Render markdown files**
   ```bash
   # Open markdown in split-pane view
   mdview README.md
   mdview documentation.md
   ```

2. **Markdown features**
   - Syntax highlighting for code blocks
   - Interactive tables and lists
   - Clickable links (open in new tab)
   - Math rendering with KaTeX
   - Mermaid diagram support

## AI Assistant

### Basic AI Interaction

1. **Enable AI assistant**
   - Go to Settings → AI Assistant
   - Choose provider (OpenAI, Anthropic, Local)
   - Enter API key if required
   - Enable desired features

2. **Text-based queries**
   ```bash
   # Ask for command suggestions
   ai suggest "how to find large files"

   # Explain command output
   ai explain "ls -la output"

   # Get help with errors
   ai help "permission denied error"
   ```

3. **AI chat sidebar**
   - Click AI icon in sidebar
   - Type questions or commands
   - Get contextual responses
   - View conversation history

### Voice Input

1. **Enable voice features**
   - Go to Settings → AI Assistant → Voice
   - Grant microphone permissions
   - Test microphone and speaker

2. **Voice commands**
   - **Activate**: Press and hold 'Ctrl+Space'
   - **Speak**: Give voice command or question
   - **Release**: Let go to process
   - **Listen**: AI responds with voice (optional)

3. **Voice command examples**
   - "List files in current directory"
   - "Create a new folder called projects"
   - "Show git status"
   - "Explain this error message"

### AI Modes

1. **Inline suggestions**
   - Type partial command
   - See AI suggestions appear
   - Press Tab to accept suggestion
   - Press Esc to dismiss

2. **Sidebar chat**
   - Full conversation interface
   - Context from terminal session
   - Code examples and explanations
   - Command history integration

3. **Voice-only mode**
   - Hands-free operation
   - Speak commands and questions
   - Audio responses
   - Visual confirmations for actions

## Session Recording

### Recording Sessions

1. **Start recording**
   ```bash
   # Manual recording control
   record start

   # Or use interface button
   # Click record button in status bar
   ```

2. **Recording settings**
   - **Auto-record**: Enable in settings for all sessions
   - **Quality**: Choose compression level (1-9)
   - **Duration**: Set maximum recording length
   - **Storage**: Local or cloud storage

3. **Stop recording**
   ```bash
   record stop

   # Or click stop button in interface
   ```

### Playback and Management

1. **List recordings**
   ```bash
   # View all recordings
   record list

   # Filter by date
   record list --since "2025-09-20"
   ```

2. **Playback recordings**
   ```bash
   # Play recording by ID
   record play 123e4567-e89b-12d3-a456-426614174000

   # Or use the recordings panel
   ```

3. **Playback controls**
   - **Play/Pause**: Spacebar
   - **Speed**: 0.5x, 1x, 2x, 4x speed
   - **Seek**: Progress bar or arrow keys
   - **Skip**: Jump to next/previous command
   - **Timeline**: Click to jump to time

### Export Options

1. **Export formats**
   ```bash
   # Export as JSON (original format)
   record export --format json recording-id

   # Export as GIF animation
   record export --format gif recording-id

   # Export as MP4 video
   record export --format mp4 recording-id

   # Export as text log
   record export --format txt recording-id
   ```

2. **Export settings**
   - **Resolution**: Original, 720p, 1080p
   - **Frame rate**: 15, 30, 60 FPS
   - **Duration**: Full or time range
   - **Quality**: Compression settings

### Sharing Recordings

1. **Create share links**
   ```bash
   # Create public share link
   record share recording-id

   # Create password-protected link
   record share --password mypassword recording-id

   # Create expiring link (7 days)
   record share --expires 7d recording-id
   ```

2. **Share settings**
   - **View-only**: Recipients can only watch
   - **Download**: Allow downloading original
   - **Comments**: Enable comments on playback
   - **Analytics**: Track view counts and duration

## Customization

### Themes

1. **Apply built-in themes**
   - Go to Settings → Appearance → Themes
   - Browse available themes
   - Click to preview
   - Click "Apply" to use

2. **Popular built-in themes**
   - **Dark Ocean**: Deep blue with teal accents
   - **Monokai Pro**: Classic dark with vibrant colors
   - **Solarized Dark**: Popular programmer theme
   - **Dracula**: Purple and pink dark theme
   - **Light Modern**: Clean light theme

3. **Import custom themes**
   ```bash
   # Import theme from file
   theme import my-theme.json

   # Import from URL
   theme import https://example.com/theme.json
   ```

4. **Create custom themes**
   - Use the theme editor in settings
   - Customize colors, fonts, animations
   - Preview changes in real-time
   - Export for sharing

### Extensions

1. **Browse extensions**
   - Go to Settings → Extensions → Browse
   - Categories: Productivity, Development, Utilities
   - Search by name or functionality
   - Read descriptions and reviews

2. **Popular extensions**
   - **Git Enhanced**: Advanced git commands and visualization
   - **File Manager**: GUI file operations
   - **System Monitor**: Real-time system stats
   - **Color Picker**: Select colors from terminal
   - **ASCII Art Generator**: Create text art

3. **Install extensions**
   ```bash
   # Install by name
   ext install git-enhanced

   # Install from file
   ext install extension-package.zip

   # Install from repository
   ext install https://github.com/user/terminal-extension
   ```

4. **Manage extensions**
   ```bash
   # List installed extensions
   ext list

   # Enable/disable extension
   ext enable git-enhanced
   ext disable file-manager

   # Update extensions
   ext update --all

   # Configure extension
   ext config git-enhanced
   ```

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