"""
Pipeline Visualization Routes - Tab 2

Loads pipeline results and audio files for display.
"""

import json
import sys
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

# Add project root to path for imports
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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


def get_derivation_data() -> Dict[str, Any]:
    """Get enriched derivation data for visualization."""
    from lib.archetypes import ARCHETYPES, ArchetypeName, COMPATIBILITY_MATRIX
    from lib.archetype_selector import ARCHETYPE_PROFILES
    
    pipeline = load_pipeline_results()
    
    if "error" in pipeline:
        return {"error": pipeline["error"]}
    
    # Extract input metrics
    analysis = pipeline.get("analysis", {})
    input_metrics = {
        "valence": analysis.get("emotional_valence", 0),
        "tension": analysis.get("tension_level", 0),
        "hope": analysis.get("hope_factor", 0),
        "energy": analysis.get("energy_level", "medium"),
    }
    
    # Scoring weights (from archetype_selector.py)
    scoring_weights = {
        "valence": 0.30,
        "tension": 0.25,
        "hope": 0.30,
        "energy": 0.15,
    }
    
    # Build archetype profiles with definitions
    archetypes_data = {}
    for name in ArchetypeName:
        profile = ARCHETYPE_PROFILES[name]
        descriptor = ARCHETYPES[name]
        
        archetypes_data[name.value] = {
            "name": name.value,
            "display_name": name.value.replace("_", " ").title(),
            # Profile (ideal values)
            "profile": {
                "valence_center": profile.valence_center,
                "valence_tolerance": profile.valence_tolerance,
                "tension_center": profile.tension_center,
                "tension_tolerance": profile.tension_tolerance,
                "hope_center": profile.hope_center,
                "hope_tolerance": profile.hope_tolerance,
                "preferred_energy": profile.preferred_energy,
            },
            # Music descriptor
            "descriptor": {
                "genre": descriptor.genre,
                "instruments": descriptor.instruments,
                "mood_musical": descriptor.mood_musical,
                "mood_emotional": descriptor.mood_emotional,
                "tempo_bpm": descriptor.tempo_bpm,
                "tempo_value": descriptor.tempo_value,
                "technical": descriptor.technical,
            },
            # Compatible archetypes for blending
            "compatible_with": [a.value for a in COMPATIBILITY_MATRIX.get(name, [])],
        }
    
    # Selection results (from pipeline)
    selection = pipeline.get("selection", {})
    primary = selection.get("primary")
    secondary = selection.get("secondary")
    blend_ratio = selection.get("blend_ratio")
    
    # All scores with component breakdown
    all_scores = selection.get("all_scores", [])
    
    # Prompt components (what was actually used)
    prompt_data = pipeline.get("prompt", {})
    prompt_components = prompt_data.get("components", {})
    
    return {
        "input_metrics": input_metrics,
        "scoring_weights": scoring_weights,
        "archetypes": archetypes_data,
        "selection": {
            "primary": primary,
            "secondary": secondary,
            "blend_ratio": blend_ratio,
            "all_scores": all_scores,
        },
        "prompt": {
            "final_prompt": prompt_data.get("prompt", ""),
            "components": {
                "genre": prompt_components.get("genre"),
                "instruments": prompt_components.get("base_instruments", []),
                "moods": prompt_components.get("base_moods", []),
                "tempo": prompt_components.get("tempo_final"),
                "intensity": prompt_components.get("intensity_level"),
                "instrument_variant": prompt_components.get("instrument_variant", 0),
                "texture_timbre": prompt_components.get("texture_timbre", []),
                "texture_movement": prompt_components.get("texture_movement", []),
                "texture_harmonic": prompt_components.get("texture_harmonic", []),
                "source_themes": prompt_components.get("source_themes", []),
            },
        },
        "themes": analysis.get("dominant_themes", []),
        "date": pipeline.get("date"),
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


@router.get("/api/derivation")
async def api_derivation():
    """API endpoint for derivation visualization data."""
    return JSONResponse(get_derivation_data())


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
