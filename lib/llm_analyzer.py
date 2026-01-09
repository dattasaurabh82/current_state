"""
LLM Analyzer - News to Music Prompt Pipeline

Orchestrates the full pipeline:
1. LLM Analysis - Structured mood extraction (single LLM call)
2. Archetype Selection - Rule-based scoring
3. Prompt Building - 3-layer prompt construction
4. Visualization - SVG generation

Returns: (music_prompt, analysis_dict)
"""

import os
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Strip whitespace/quotes from the Replicate API token
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token.strip().strip('"')

if not os.getenv("REPLICATE_API_TOKEN"):
    raise ValueError("REPLICATE_API_TOKEN not found in .env file.")

import replicate

from lib.archetypes import ArchetypeName
from lib.archetype_selector import NewsAnalysis, select_archetypes
from lib.music_prompt_builder import build_prompt_from_selection
from lib.visualizations import generate_all_visualizations
from lib.generation_backup import backup_generation_results


# =============================================================================
# CONFIGURATION
# =============================================================================

# Output directories
GENERATION_RESULTS_DIR = Path("generation_results")

# LLM Configuration
LLM_MODEL = "meta/meta-llama-3-70b-instruct"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 500


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are a world news mood analyzer. Your task is to analyze news headlines and extract structured emotional dimensions.

You MUST output ONLY a valid JSON object with these exact fields:

emotional_valence: float from -1 to 1
tension_level: float from 0 to 1
hope_factor: float from 0 to 1
energy_level: one of "low", "medium", "high"
dominant_themes: list of up to 5 theme strings
summary: one sentence summary string

Field definitions:
- emotional_valence: Overall emotional tone. -1 = very negative (crisis, tragedy), 0 = neutral, +1 = very positive (celebration, breakthrough)
- tension_level: Amount of conflict/uncertainty. 0 = calm/stable, 1 = high tension/conflict
- hope_factor: Presence of hope or optimism. 0 = hopeless/dire, 1 = very hopeful/optimistic
- energy_level: Overall energy/intensity. "low" = quiet/reflective, "medium" = normal activity, "high" = intense/urgent
- dominant_themes: Up to 5 key themes (e.g., "conflict", "economy", "science", "environment", "politics")
- summary: One sentence capturing the day's overall mood

IMPORTANT:
- Output ONLY the JSON object, no other text
- All numeric values must be valid floats
- dominant_themes must be a list with max 5 items
- Be nuanced - most days are mixed, not purely positive or negative"""


def _build_prompt_template(system_prompt: str) -> str:
    """Build Llama 3 format prompt template."""
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{prompt}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""


PROMPT_TEMPLATE = _build_prompt_template(SYSTEM_PROMPT)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_headlines(articles: List[Dict]) -> List[str]:
    """Extract formatted headlines from articles."""
    headlines = []
    for article in articles:
        title = article.get("title", "")
        source = article.get("source", {})
        source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)
        if title:
            headlines.append(f"- {title} (Source: {source_name})")
    return headlines


def _call_llm(user_prompt: str) -> Optional[str]:
    """Make the LLM API call."""
    try:
        logger.info("[LLM] Calling Llama 3 70B for news analysis...")
        
        output_chunks = replicate.run(
            LLM_MODEL,
            input={
                "prompt": user_prompt,
                "prompt_template": PROMPT_TEMPLATE,
                "temperature": LLM_TEMPERATURE,
                "max_new_tokens": LLM_MAX_TOKENS,
                "frequency_penalty": 0.1
            }
        )
        
        full_output = "".join(output_chunks)
        logger.info("[LLM] Response received")
        return full_output.strip()
        
    except Exception as e:
        logger.error(f"[LLM] API call failed: {e}")
        return None


def _parse_llm_response(response: str) -> Optional[NewsAnalysis]:
    """Parse LLM response into NewsAnalysis."""
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if not match:
            logger.error(f"[LLM] No JSON found in response: {response[:200]}")
            return None
        
        json_str = match.group(0)
        data = json.loads(json_str)
        
        analysis = NewsAnalysis(
            emotional_valence=max(-1, min(1, float(data.get("emotional_valence", 0)))),
            tension_level=max(0, min(1, float(data.get("tension_level", 0.5)))),
            hope_factor=max(0, min(1, float(data.get("hope_factor", 0.5)))),
            energy_level=str(data.get("energy_level", "medium")).lower(),
            dominant_themes=list(data.get("dominant_themes", []))[:5],
            summary=str(data.get("summary", ""))
        )
        
        if analysis.energy_level not in ["low", "medium", "high"]:
            analysis.energy_level = "medium"
        
        logger.info(f"[LLM] Parsed: valence={analysis.emotional_valence:+.2f}, "
                   f"tension={analysis.tension_level:.2f}, hope={analysis.hope_factor:.2f}")
        
        return analysis
        
    except json.JSONDecodeError as e:
        logger.error(f"[LLM] JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"[LLM] Parse error: {e}")
        return None


def _analyze_news_with_llm(headlines: List[str]) -> Optional[NewsAnalysis]:
    """Analyze news headlines using LLM."""
    headlines_str = "\n".join(headlines)
    
    json_example = '''{
    "emotional_valence": 0.3,
    "tension_level": 0.5,
    "hope_factor": 0.6,
    "energy_level": "medium",
    "dominant_themes": ["economy", "politics", "science"],
    "summary": "A mixed day with economic concerns balanced by scientific progress."
}'''
    
    user_prompt = f"""Analyze these news headlines and provide a structured mood assessment:

{headlines_str}

Output format example:
{json_example}

Remember: Output ONLY a valid JSON object with the required fields. No other text."""

    result = _call_llm(user_prompt)
    if result is None:
        return None
    
    return _parse_llm_response(result)


def _save_pipeline_results(
    analysis: NewsAnalysis,
    selection_dict: Dict,
    prompt_result_dict: Dict,
    output_dir: Path,
    date_str: str,
):
    """Save all pipeline results to files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save combined results
    results = {
        "timestamp": datetime.now().isoformat(),
        "date": date_str,
        "analysis": {
            "emotional_valence": analysis.emotional_valence,
            "tension_level": analysis.tension_level,
            "hope_factor": analysis.hope_factor,
            "energy_level": analysis.energy_level,
            "dominant_themes": analysis.dominant_themes,
            "summary": analysis.summary,
        },
        "selection": selection_dict,
        "prompt": prompt_result_dict,
    }
    
    with open(output_dir / "pipeline_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save prompt text separately for easy access
    with open(output_dir / "prompt.txt", 'w') as f:
        f.write(prompt_result_dict.get("prompt", ""))
    
    logger.info(f"[Pipeline] Results saved to {output_dir}")


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def generate_music_prompt_from_news(articles: List[Dict]) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Orchestrates the full pipeline: LLM analysis → archetype selection → prompt building.
    
    Args:
        articles: List of news article dicts with 'title' and 'source' keys
        
    Returns:
        Tuple of (music_prompt, analysis_dict) or (None, None) on failure
    """
    logger.info("=" * 60)
    logger.info("[Pipeline] STARTING MUSIC GENERATION PIPELINE")
    logger.info("=" * 60)
    
    # Extract headlines
    headlines = _extract_headlines(articles)
    if not headlines:
        logger.warning("[Pipeline] No valid headlines found")
        return None, None
    
    logger.info(f"[Pipeline] Processing {len(headlines)} headlines")
    
    # Get today's date for seed and output directory
    today = date.today()
    date_str = today.isoformat()
    
    # ==========================================================================
    # STEP 1: LLM Analysis
    # ==========================================================================
    logger.info("[Pipeline] Step 1: LLM Analysis")
    
    analysis = _analyze_news_with_llm(headlines)
    if analysis is None:
        logger.error("[Pipeline] LLM analysis failed")
        return None, None
    
    # ==========================================================================
    # STEP 2: Archetype Selection (Rule-Based)
    # ==========================================================================
    logger.info("[Pipeline] Step 2: Archetype Selection")
    
    selection = select_archetypes(analysis)
    selection_dict = selection.to_dict()
    
    # ==========================================================================
    # STEP 3: Prompt Building
    # ==========================================================================
    logger.info("[Pipeline] Step 3: Prompt Building")
    
    prompt_result = build_prompt_from_selection(
        selection=selection_dict,
        themes=analysis.dominant_themes,
        date_seed=today,
    )
    prompt_result_dict = prompt_result.to_dict()
    
    # ==========================================================================
    # STEP 4: Save Results & Visualizations
    # ==========================================================================
    logger.info("[Pipeline] Step 4: Saving Results & Visualizations")
    
    output_dir = GENERATION_RESULTS_DIR
    viz_dir = output_dir / "visualizations"
    
    # Generate visualizations
    try:
        viz_files = generate_all_visualizations(
            analysis={
                "emotional_valence": analysis.emotional_valence,
                "tension_level": analysis.tension_level,
                "hope_factor": analysis.hope_factor,
                "energy_level": analysis.energy_level,
            },
            selection=selection_dict,
            prompt_components=prompt_result_dict.get("components", {}),
            output_dir=str(viz_dir),
            date_str=date_str,
        )
        logger.info(f"[Pipeline] Generated {len(viz_files)} visualizations")
    except Exception as e:
        logger.warning(f"[Pipeline] Visualization generation failed: {e}")
    
    # Save pipeline results
    _save_pipeline_results(
        analysis=analysis,
        selection_dict=selection_dict,
        prompt_result_dict=prompt_result_dict,
        output_dir=output_dir,
        date_str=date_str,
    )
    
    # ==========================================================================
    # STEP 5: Backup to Dropbox (optional)
    # ==========================================================================
    backup_generation_results()
    
    # ==========================================================================
    # DONE
    # ==========================================================================
    logger.info("=" * 60)
    logger.success(f"[Pipeline] COMPLETE - Prompt: {prompt_result.prompt[:80]}...")
    logger.info("=" * 60)
    
    # Return in same format as old API
    analysis_dict = {
        "emotional_valence": analysis.emotional_valence,
        "tension_level": analysis.tension_level,
        "hope_factor": analysis.hope_factor,
        "energy_level": analysis.energy_level,
        "dominant_themes": analysis.dominant_themes,
        "summary": analysis.summary,
        "archetype_primary": selection.primary.value,
        "archetype_secondary": selection.secondary.value if selection.secondary else None,
    }
    
    return prompt_result.prompt, analysis_dict
