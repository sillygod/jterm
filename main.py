#!/usr/bin/env python3
"""
PyInstaller entry point for jterm desktop application.

This wrapper ensures the src package is properly accessible when bundled.
"""
import sys
import os

# Add current directory to Python path for src package access
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    import argparse

    # Parse command-line arguments for desktop mode
    parser = argparse.ArgumentParser(description="Web Terminal Server")
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    # Import app from src package
    from src.main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
