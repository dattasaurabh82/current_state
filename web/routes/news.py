"""
News Bulletin Routes - Tab 1

Loads news data from the latest news_data_*.json file and formats it for the template.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
NEWS_FILE_PATTERN = "news_data_*.json"
NEWS_FILE_PREFIX = "news_data_"

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data Loading
# -----------------------------------------------------------------------------

def get_latest_news_file() -> Optional[Path]:
    """
    Find the most recent news_data_*.json file in the project root.
    
    Returns:
        Path to the most recent news file, or None if no files found.
        Files are sorted by filename (which contains date) in descending order.
    """
    news_files = list(PROJECT_ROOT.glob(NEWS_FILE_PATTERN))
    if not news_files:
        return None
    
    # Sort by filename descending (news_data_2026-01-10.json > news_data_2026-01-09.json)
    news_files.sort(key=lambda p: p.name, reverse=True)
    return news_files[0]


def _parse_regions(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform raw news data into a list of region dictionaries.
    
    Args:
        raw_data: Raw JSON data from news file, keyed by region name.
        
    Returns:
        List of region dicts with keys: key, name, language, articles, count
    """
    regions = []
    
    for region_key, region_data in raw_data.items():
        if not isinstance(region_data, dict):
            logger.warning(f"Skipping invalid region data for '{region_key}'")
            continue
            
        # Clean up region name: "English_Speaking" -> "English Speaking"
        region_name = region_key.replace("_", " ")
        
        articles = region_data.get("articles", [])
        if not isinstance(articles, list):
            articles = []
            
        regions.append({
            "key": region_key,
            "name": region_name,
            "language": region_data.get("language", "en"),
            "articles": articles,
            "count": len(articles),
        })
    
    return regions


def load_news_data() -> Dict[str, Any]:
    """
    Load and parse news data from the latest news file.
    
    Returns:
        Dictionary containing:
        - error: Error message string, or None if successful
        - regions: List of region data dicts
        - date: Date string extracted from filename (YYYY-MM-DD)
        - file: Filename of the loaded news file
    """
    news_file = get_latest_news_file()
    
    if news_file is None:
        logger.info("No news data files found")
        return {
            "error": "No news data found",
            "regions": [],
            "date": None,
            "file": None,
        }
    
    if not news_file.exists():
        logger.warning(f"News file disappeared: {news_file}")
        return {
            "error": "News file not found",
            "regions": [],
            "date": None,
            "file": news_file.name,
        }
    
    try:
        with open(news_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        
        # Extract date from filename (news_data_2026-01-09.json -> 2026-01-09)
        date_str = news_file.stem.replace(NEWS_FILE_PREFIX, "")
        
        regions = _parse_regions(raw_data)
        
        logger.debug(f"Loaded {sum(r['count'] for r in regions)} articles from {news_file.name}")
        
        return {
            "error": None,
            "regions": regions,
            "date": date_str,
            "file": news_file.name,
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {news_file.name}: {e}")
        return {
            "error": f"Invalid JSON: {e}",
            "regions": [],
            "date": None,
            "file": news_file.name,
        }
    except Exception as e:
        logger.exception(f"Error loading news data from {news_file.name}")
        return {
            "error": str(e),
            "regions": [],
            "date": None,
            "file": news_file.name,
        }


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def get_news_context() -> Dict[str, Any]:
    """
    Get news data formatted for Jinja2 template context.
    
    This is the main entry point called by app.py.
    
    Returns:
        Dictionary ready to be passed to the template.
    """
    return load_news_data()
