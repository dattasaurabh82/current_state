"""
World Theme Music Player - Web Dashboard

A TUI-style web interface for monitoring the news-to-music generation pipeline.

Usage:
    # Development
    uv run uvicorn web.app:app --reload --host 0.0.0.0 --port 7070
    
    # Production
    uv run uvicorn web.app:app --host 127.0.0.1 --port 7070

Modules:
    app: FastAPI application and routes
    routes.news: News bulletin data loading
    routes.pipeline: Pipeline visualization and audio APIs
    routes.logs: WebSocket log streaming
"""

__version__ = "1.0.0"
__author__ = "Saurabh Datta"
