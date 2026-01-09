"""
World Theme Music Player - Web Dashboard

TUI-style web interface for monitoring:
- Tab 1: News Bulletin
- Tab 2: Pipeline Visualization  
- Tab 3: Live Logs

Run: uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Paths
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"
PROJECT_ROOT = WEB_DIR.parent

# FastAPI app
app = FastAPI(
    title="World Theme Music Player",
    description="TUI-style dashboard for news-to-music pipeline",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Redirect to news tab (default)."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "active_tab": "news",
    })


@app.get("/news", response_class=HTMLResponse)
async def news_tab(request: Request):
    """Tab 1: News Bulletin."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "active_tab": "news",
    })


@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_tab(request: Request):
    """Tab 2: Pipeline Visualization."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "active_tab": "pipeline",
    })


@app.get("/logs", response_class=HTMLResponse)
async def logs_tab(request: Request):
    """Tab 3: Live Logs."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "active_tab": "logs",
    })


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
