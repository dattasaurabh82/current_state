"""
Web Routes Package

This package contains route handlers for the web dashboard:

- news.py: News bulletin data loading (Tab 1)
- pipeline.py: Pipeline visualization and audio APIs (Tab 2)
- logs.py: WebSocket log streaming (Tab 3)
"""

from web.routes.news import get_news_context
from web.routes.pipeline import router as pipeline_router, get_pipeline_context
from web.routes.logs import router as logs_router

__all__ = [
    "get_news_context",
    "pipeline_router",
    "get_pipeline_context",
    "logs_router",
]
