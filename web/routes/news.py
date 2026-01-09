"""
News Bulletin Routes - Tab 1

Loads news data from generation results and serves to template.
"""

import json
from pathlib import Path
from datetime import date

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
TEMPLATES_DIR = WEB_DIR / "templates"

templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_latest_news_file() -> Path | None:
    """Find the most recent news_data_*.json file."""
    news_files = list(PROJECT_ROOT.glob("news_data_*.json"))
    if not news_files:
        return None
    # Sort by date in filename (most recent first)
    news_files.sort(reverse=True)
    return news_files[0]


def load_news_data() -> dict:
    """Load news data from the latest news file."""
    news_file = get_latest_news_file()
    
    if not news_file or not news_file.exists():
        return {
            "error": "No news data found",
            "regions": {},
            "date": None,
            "file": None,
        }
    
    try:
        with open(news_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        # Extract date from filename (news_data_2026-01-09.json -> 2026-01-09)
        date_str = news_file.stem.replace("news_data_", "")
        
        # Transform data for template
        regions = []
        for region_key, region_data in raw_data.items():
            # Clean up region name: "English_Speaking" -> "English Speaking"
            region_name = region_key.replace("_", " ")
            
            articles = region_data.get("articles", [])
            language = region_data.get("language", "en")
            
            regions.append({
                "key": region_key,
                "name": region_name,
                "language": language,
                "articles": articles,
                "count": len(articles),
            })
        
        return {
            "error": None,
            "regions": regions,
            "date": date_str,
            "file": news_file.name,
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "regions": [],
            "date": None,
            "file": news_file.name if news_file else None,
        }


def get_news_context() -> dict:
    """Get news data formatted for template context."""
    return load_news_data()
