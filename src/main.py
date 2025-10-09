"""FastAPI main application for Web Terminal."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.database.base import engine, AsyncSessionLocal
from src.websockets.terminal_handler import get_terminal_handler
from src.websockets.ai_handler import get_ai_handler
from src.websockets.recording_handler import get_recording_handler
from src.api.media_endpoints import router as media_router
from src.api.ai_endpoints import router as ai_router
from src.api.recording_endpoints import router as recording_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print("🚀 Web Terminal starting up...")

    # Test database connection
    try:
        async with engine.connect() as conn:
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    # Create default user if not exists
    try:
        from src.models.user_profile import UserProfile
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # Check if default user exists
            query = select(UserProfile).where(
                UserProfile.user_id == "00000000-0000-0000-0000-000000000001"
            )
            result = await db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                # Create default user
                default_user = UserProfile(
                    user_id="00000000-0000-0000-0000-000000000001",
                    username="default",
                    email="default@localhost",
                    display_name="Default User",
                    preferences={},
                    default_shell="bash",
                    keyboard_shortcuts={},
                    ai_settings={},
                    recording_settings={},
                    privacy_settings={},
                    storage_quota=1073741824,  # 1GB
                    storage_used=0,
                    is_active=True,
                    extra_metadata={}
                )
                db.add(default_user)
                await db.commit()
                print("👤 Created default user (ID: 00000000-0000-0000-0000-000000000001)")
            else:
                print("👤 Default user already exists")
    except Exception as e:
        print(f"⚠️  Warning: Could not create default user: {e}")
        print("   You may need to run: ./bin/setup_db.sh")

    yield

    # Shutdown
    print("🛑 Web Terminal shutting down...")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Web Terminal",
    description="Web-based terminal emulator with multimedia support, AI assistance, and session recording",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Web Terminal is running"}


# Root endpoint - serve main terminal page
@app.get("/")
async def index(request: Request):
    """Serve the main terminal page."""
    return templates.TemplateResponse("base.html", {"request": request})


# Settings endpoint
@app.get("/api/settings")
async def get_settings(request: Request):
    """Get settings modal content."""
    return templates.TemplateResponse("components/settings.html", {"request": request})


# Simple image viewing endpoint
@app.post("/api/media/process")
async def process_media(request: Request):
    """Process media for viewing - returns file metadata."""
    from PIL import Image
    import hashlib

    body = await request.json()
    file_path = body.get("filePath", "")
    media_type = body.get("mediaType", "image")

    # Check if file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Create a unique ID for this file based on its path
    file_id = hashlib.md5(file_path.encode()).hexdigest()

    # Store file path in a simple in-memory cache (in production, use Redis or similar)
    if not hasattr(app.state, 'file_cache'):
        app.state.file_cache = {}
    app.state.file_cache[file_id] = file_path

    # Determine mime type
    ext = os.path.splitext(file_path)[1].lower()

    if media_type == "image":
        try:
            # Get image dimensions
            img = Image.open(file_path)
            width, height = img.size

            mime_types = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.webp': 'image/webp', '.bmp': 'image/bmp',
                '.svg': 'image/svg+xml'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')

            return {
                "fileName": os.path.basename(file_path),
                "url": f"/api/media/serve/{file_id}",
                "dimensions": {"width": width, "height": height},
                "fileSize": os.path.getsize(file_path),
                "mimeType": mime_type
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")

    elif media_type == "video":
        mime_types = {
            '.mp4': 'video/mp4', '.webm': 'video/webm',
            '.ogg': 'video/ogg', '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo'
        }
        mime_type = mime_types.get(ext, 'video/mp4')

        return {
            "fileName": os.path.basename(file_path),
            "url": f"/api/media/serve/{file_id}",
            "fileSize": os.path.getsize(file_path),
            "mimeType": mime_type
        }

    raise HTTPException(status_code=400, detail="Unsupported media type")


# Serve media files
@app.get("/api/media/serve/{file_id}")
async def serve_media(file_id: str):
    """Serve media file from filesystem."""
    if not hasattr(app.state, 'file_cache'):
        raise HTTPException(status_code=404, detail="File not found")

    file_path = app.state.file_cache.get(file_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


# Markdown rendering endpoint
@app.post("/api/media/markdown")
async def render_markdown(request: Request, filePath: str = ""):
    """Render markdown file."""
    import markdown

    # Try to get from form data first, then JSON
    if not filePath:
        try:
            body = await request.json()
            file_path = body.get("filePath", "")
        except:
            form = await request.form()
            file_path = form.get("filePath", "")
    else:
        file_path = filePath

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        # Read markdown file
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['fenced_code', 'tables', 'toc', 'codehilite']
        )

        # Return simple HTML response with GitHub-flavored styling
        simple_html = f"""
        <div class="markdown-viewer-simple">
            <div class="markdown-header-simple">
                <span class="markdown-title">{os.path.basename(file_path)}</span>
                <button class="btn btn-icon" onclick="document.getElementById('markdown-overlay').classList.remove('visible')">✕</button>
            </div>
            <div class="markdown-content-simple markdown-body">
                {html_content}
            </div>
        </div>
        <style>
        .markdown-viewer-simple {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #0d1117;
            z-index: 1000;
            display: flex;
            flex-direction: column;
        }}
        .markdown-header-simple {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            background: #161b22;
            border-bottom: 1px solid #30363d;
        }}
        .markdown-content-simple {{
            flex: 1;
            overflow-y: auto;
            padding: 2rem;
            max-width: 980px;
            margin: 0 auto;
            width: 100%;
        }}

        /* GitHub-flavored markdown styles */
        .markdown-body {{
            color: #c9d1d9;
            font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
            font-size: 16px;
            line-height: 1.6;
        }}
        .markdown-body h1, .markdown-body h2 {{
            border-bottom: 1px solid #21262d;
            padding-bottom: 0.3em;
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
        }}
        .markdown-body h1 {{ font-size: 2em; }}
        .markdown-body h2 {{ font-size: 1.5em; }}
        .markdown-body h3 {{ font-size: 1.25em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
        .markdown-body h4 {{ font-size: 1em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
        .markdown-body p {{ margin-bottom: 16px; }}
        .markdown-body a {{ color: #58a6ff; text-decoration: none; }}
        .markdown-body a:hover {{ text-decoration: underline; }}
        .markdown-body code {{
            background: rgba(110,118,129,0.4);
            padding: 0.2em 0.4em;
            border-radius: 6px;
            font-family: ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace;
            font-size: 85%;
        }}
        .markdown-body pre {{
            background: #161b22;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            margin-bottom: 16px;
            border: 1px solid #30363d;
        }}
        .markdown-body pre code {{
            background: none;
            padding: 0;
            font-size: 100%;
        }}
        .markdown-body table {{
            border-collapse: collapse;
            width: 100%;
            margin: 16px 0;
            border-spacing: 0;
        }}
        .markdown-body th, .markdown-body td {{
            border: 1px solid #30363d;
            padding: 6px 13px;
        }}
        .markdown-body th {{
            background: #161b22;
            font-weight: 600;
        }}
        .markdown-body tr:nth-child(2n) {{
            background: #0d1117;
        }}
        .markdown-body blockquote {{
            border-left: 4px solid #30363d;
            padding-left: 16px;
            margin: 16px 0;
            color: #8b949e;
        }}
        .markdown-body ul, .markdown-body ol {{
            margin-bottom: 16px;
            padding-left: 2em;
        }}
        .markdown-body li {{
            margin-top: 0.25em;
        }}
        .markdown-body hr {{
            border: 0;
            border-top: 1px solid #21262d;
            margin: 24px 0;
        }}
        .markdown-body img {{
            max-width: 100%;
            border-radius: 6px;
        }}
        </style>
        """
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=simple_html)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to render markdown: {str(e)}")


# HTML preview endpoint
@app.post("/api/media/html-preview")
async def preview_html(request: Request, filePath: str = "", allowJS: bool = False):
    """Preview HTML file with sandboxing."""
    # Try to get from form data first, then JSON
    if not filePath:
        try:
            body = await request.json()
            file_path = body.get("filePath", "")
            allowJS = body.get("allowJS", False)
        except:
            form = await request.form()
            file_path = form.get("filePath", "")
            allowJS = form.get("allowJS", "false").lower() == "true"
    else:
        file_path = filePath

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Create a hash ID for the file
    import hashlib
    file_id = hashlib.md5(file_path.encode()).hexdigest()

    # Store file path in cache
    if not hasattr(app.state, 'file_cache'):
        app.state.file_cache = {}
    app.state.file_cache[file_id] = file_path

    # Determine sandbox permissions
    if allowJS:
        sandbox_permissions = "allow-scripts allow-same-origin"
    else:
        sandbox_permissions = "allow-same-origin"

    return {
        "fileName": os.path.basename(file_path),
        "sandboxUrl": f"/api/media/serve/{file_id}",
        "sandboxPermissions": sandbox_permissions
    }


# Include routers
app.include_router(media_router)
app.include_router(ai_router)
app.include_router(recording_router)


# WebSocket endpoints
@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """Terminal WebSocket endpoint."""
    handler = await get_terminal_handler()
    await handler.handle_connection(websocket)


@app.websocket("/ws/ai")
async def ai_websocket(websocket: WebSocket):
    """AI assistant WebSocket endpoint."""
    handler = await get_ai_handler()
    await handler.handle_connection(websocket)


@app.websocket("/ws/recording/{session_id}")
async def recording_websocket(websocket: WebSocket, session_id: str):
    """Recording playback WebSocket endpoint."""
    handler = await get_recording_handler()
    await handler.handle_connection(websocket, session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )