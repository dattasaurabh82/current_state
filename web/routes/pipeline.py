"""
Pipeline Visualization Routes - Tab 2

Loads pipeline results and audio files for display.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()

# Paths
WEB_DIR = Path(__file__).parent.parent
PROJECT_ROOT = WEB_DIR.parent
GENERATION_RESULTS_DIR = PROJECT_ROOT / "generation_results"
MUSIC_DIR = PROJECT_ROOT / "music_generated"


def load_pipeline_results() -> Dict[str, Any]:
    """Load the latest pipeline results."""
    results_file = GENERATION_RESULTS_DIR / "pipeline_results.json"
    
    if not results_file.exists():
        return {"error": "No pipeline results found"}
    
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Parse timestamp for display
        if "timestamp" in data:
            try:
                dt = datetime.fromisoformat(data["timestamp"])
                data["timestamp_display"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                data["timestamp_display"] = data["timestamp"]
        
        return data
    
    except Exception as e:
        return {"error": str(e)}


def get_audio_files() -> List[Dict[str, Any]]:
    """Get list of available audio files with metadata."""
    if not MUSIC_DIR.exists():
        return []
    
    audio_files = []
    
    for filepath in sorted(MUSIC_DIR.glob("*.wav"), reverse=True):
        # Skip placeholder and test files
        if filepath.name.startswith("generated_music") or filepath.name.startswith("POST_PROCESSOR"):
            continue
        
        # Parse date from filename: world_theme_2026-01-09_20-33-17.wav
        date_str = ""
        time_str = ""
        try:
            parts = filepath.stem.split("_")
            if len(parts) >= 3:
                date_str = parts[2]  # 2026-01-09
                if len(parts) >= 4:
                    time_str = parts[3].replace("-", ":")  # 20:33:17
        except:
            pass
        
        # Get file size
        try:
            size_bytes = filepath.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            size_display = f"{size_mb:.1f} MB"
        except:
            size_display = "Unknown"
        
        audio_files.append({
            "filename": filepath.name,
            "date": date_str,
            "time": time_str,
            "size": size_display,
            "url": f"/audio/{filepath.name}",
        })
    
    return audio_files


def get_pipeline_context() -> Dict[str, Any]:
    """Get full pipeline context for template."""
    pipeline = load_pipeline_results()
    audio_files = get_audio_files()
    
    return {
        "pipeline": pipeline,
        "audio_files": audio_files,
        "audio_count": len(audio_files),
    }


# =============================================================================
# API ROUTES
# =============================================================================

@router.get("/api/pipeline")
async def api_pipeline():
    """API endpoint for pipeline results."""
    return JSONResponse(get_pipeline_context())


@router.get("/api/audio-files")
async def api_audio_files():
    """API endpoint for audio files list (for polling)."""
    return JSONResponse({
        "files": get_audio_files(),
        "count": len(get_audio_files()),
        "timestamp": datetime.now().isoformat(),
    })


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio file."""
    filepath = MUSIC_DIR / filename
    
    if not filepath.exists() or not filepath.suffix == ".wav":
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    return FileResponse(
        filepath,
        media_type="audio/wav",
        filename=filename,
    )
