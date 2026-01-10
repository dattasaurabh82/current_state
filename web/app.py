"""
World Theme Music Player - Web Dashboard

TUI-style web interface for monitoring the news-to-music pipeline.

Tabs:
- Tab 1 (News): Today's news headlines grouped by region
- Tab 2 (Pipeline): Interactive visualization + audio player
- Tab 3 (Logs): Live streaming logs via WebSocket

Run in development:
    uv run uvicorn web.app:app --reload --host 0.0.0.0 --port 7070

Run in production:
    uv run uvicorn web.app:app --host 127.0.0.1 --port 7070
"""

import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Route modules
from web.routes.news import get_news_context
from web.routes.pipeline import router as pipeline_router, get_pipeline_context
from web.routes.logs import router as logs_router

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Application Setup
# -----------------------------------------------------------------------------

app = FastAPI(
    title="World Theme Music Player",
    description="TUI-style dashboard for the news-to-music generation pipeline",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API routers
app.include_router(pipeline_router, tags=["Pipeline"])
app.include_router(logs_router, tags=["Logs"])

# Template engine
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# -----------------------------------------------------------------------------
# Template Helpers
# -----------------------------------------------------------------------------

def _render_template(
    request: Request,
    active_tab: str,
    context: Dict[str, Any] = None,
) -> HTMLResponse:
    """
    Render the base template with given tab and context.
    
    Args:
        request: FastAPI request object
        active_tab: Which tab is active ("news", "pipeline", "logs")
        context: Additional template context
        
    Returns:
        Rendered HTML response
    """
    template_context = {
        "request": request,
        "active_tab": active_tab,
    }
    
    if context:
        template_context.update(context)
    
    return templates.TemplateResponse("base.html", template_context)


# -----------------------------------------------------------------------------
# Page Routes
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """
    Home page - redirects to news tab.
    
    The news tab is the default landing page as it shows
    the day's headlines at a glance.
    """
    news_data = get_news_context()
    return _render_template(request, "news", {"news": news_data})


@app.get("/news", response_class=HTMLResponse)
async def news_tab(request: Request) -> HTMLResponse:
    """
    Tab 1: News Bulletin
    
    Displays today's fetched news headlines grouped by region.
    Data comes from news_data_YYYY-MM-DD.json files.
    """
    news_data = get_news_context()
    return _render_template(request, "news", {"news": news_data})


@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_tab(request: Request) -> HTMLResponse:
    """
    Tab 2: Pipeline Visualization
    
    Shows interactive vis-network graph of the generation pipeline
    and audio player for generated music files.
    """
    pipeline_data = get_pipeline_context()
    return _render_template(request, "pipeline", {
        "pipeline": pipeline_data.get("pipeline", {}),
        "audio_files": pipeline_data.get("audio_files", []),
        "audio_count": pipeline_data.get("audio_count", 0),
    })


@app.get("/logs", response_class=HTMLResponse)
async def logs_tab(request: Request) -> HTMLResponse:
    """
    Tab 3: Live Logs
    
    Real-time log streaming via WebSocket using xterm.js terminals.
    Shows multiple log panels for different services.
    """
    return _render_template(request, "logs")


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------

@app.get("/health", tags=["System"])
async def health() -> Dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        Simple status dict indicating the service is running.
    """
    return {"status": "ok"}


# -----------------------------------------------------------------------------
# Startup/Shutdown Events
# -----------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event() -> None:
    """Log startup information."""
    logger.info("Web dashboard starting up")
    logger.info(f"Static files: {STATIC_DIR}")
    logger.info(f"Templates: {TEMPLATES_DIR}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up on shutdown."""
    logger.info("Web dashboard shutting down")
