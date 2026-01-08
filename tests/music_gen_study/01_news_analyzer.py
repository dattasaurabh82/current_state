"""
News Analyzer Module - Step 01

Analyzes news headlines using LLM to extract structured mood dimensions.
This replaces the current two-agent approach with a single, structured output.

Output Structure:
{
    "emotional_valence": float,    # -1 (very negative) to +1 (very positive)
    "tension_level": float,        # 0 (calm) to 1 (high tension)
    "hope_factor": float,          # 0 (hopeless) to 1 (very hopeful)
    "energy_level": str,           # "low", "medium", "high"
    "dominant_themes": list[str],  # Up to 5 key themes
    "summary": str                 # One-sentence summary
}

Usage:
    python 01_news_analyzer.py                    # Uses default test data
    python 01_news_analyzer.py --file <path>      # Uses specific file
    python 01_news_analyzer.py --scenario positive # Uses test scenario
    python 01_news_analyzer.py --dry-run          # Skip LLM call, show mock
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import re

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env from project root (two levels up from tests/music_gen_study/)
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Strip whitespace/quotes from the Replicate API token (same as main project)
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token.strip().strip('"')

# Try to import replicate - graceful fallback for dry-run mode
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    print("[WARNING] replicate not installed. Use --dry-run mode.")

# Try to import rich for nice terminal output - fallback to basic print
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    print("[INFO] 'rich' not installed. Using basic output. Install with: pip install rich")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class NewsAnalysis:
    """Structured output from news analysis."""
    emotional_valence: float      # -1 to +1
    tension_level: float          # 0 to 1
    hope_factor: float            # 0 to 1
    energy_level: str             # "low", "medium", "high"
    dominant_themes: List[str]    # Up to 5 themes
    summary: str                  # One-sentence summary
    raw_response: Optional[str] = None  # For debugging
    
    def validate(self) -> bool:
        """Validate that all values are within expected ranges."""
        try:
            assert -1 <= self.emotional_valence <= 1, f"emotional_valence {self.emotional_valence} out of range [-1, 1]"
            assert 0 <= self.tension_level <= 1, f"tension_level {self.tension_level} out of range [0, 1]"
            assert 0 <= self.hope_factor <= 1, f"hope_factor {self.hope_factor} out of range [0, 1]"
            assert self.energy_level in ["low", "medium", "high"], f"energy_level '{self.energy_level}' invalid"
            assert len(self.dominant_themes) <= 5, f"too many themes: {len(self.dominant_themes)}"
            return True
        except AssertionError as e:
            print(f"[VALIDATION ERROR] {e}")
            return False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (excluding raw_response for cleaner output)."""
        d = asdict(self)
        del d['raw_response']
        return d


# =============================================================================
# SYSTEM PROMPT FOR STRUCTURED ANALYSIS
# =============================================================================

# NOTE: Curly braces are doubled to escape them in the format string
# Only {prompt} remains as the actual placeholder
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


# =============================================================================
# LLM PROMPT TEMPLATE (Llama 3 format)
# =============================================================================

def build_prompt_template(system_prompt: str) -> str:
    """Build Llama 3 format prompt template."""
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{prompt}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""


PROMPT_TEMPLATE = build_prompt_template(SYSTEM_PROMPT)


# =============================================================================
# NEWS LOADING UTILITIES
# =============================================================================

def load_news_from_file(filepath: str) -> List[Dict]:
    """Load news articles from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different file formats
    articles = []
    
    # Format 1: Direct list of articles
    if isinstance(data, list):
        articles = data
    
    # Format 2: Test data format with "articles" key
    elif "articles" in data:
        articles = data["articles"]
    
    # Format 3: Regional format (like news_data_2026-01-07.json)
    elif any(key.endswith("_Speaking") for key in data.keys()):
        for region_data in data.values():
            if isinstance(region_data, dict) and "articles" in region_data:
                articles.extend(region_data["articles"])
    
    # Format 4: Edge cases format with test_cases
    elif "test_cases" in data:
        # Return first test case by default
        if data["test_cases"]:
            articles = data["test_cases"][0].get("articles", [])
    
    return articles


def extract_headlines(articles: List[Dict]) -> List[str]:
    """Extract just the headlines from articles."""
    headlines = []
    for article in articles:
        title = article.get("title", "")
        source = article.get("source", {})
        source_name = source.get("name", "Unknown") if isinstance(source, dict) else str(source)
        if title:
            headlines.append(f"- {title} (Source: {source_name})")
    return headlines


def get_test_data_path(scenario: str) -> Path:
    """Get path to test data file for a scenario."""
    base_path = Path(__file__).parent / "test_data"
    scenario_map = {
        "positive": "news_positive.json",
        "negative": "news_negative.json",
        "mixed": "news_mixed.json",
        "edge": "news_edge_cases.json",
    }
    filename = scenario_map.get(scenario, f"news_{scenario}.json")
    return base_path / filename


# =============================================================================
# LLM ANALYSIS
# =============================================================================

def analyze_news_with_llm(headlines: List[str]) -> Optional[NewsAnalysis]:
    """
    Analyze news headlines using Replicate's Llama 3 70B.
    
    Returns structured NewsAnalysis or None if analysis fails.
    """
    if not REPLICATE_AVAILABLE:
        print("[ERROR] replicate library not available")
        return None
    
    headlines_str = "\n".join(headlines)
    
    # JSON example is in user prompt to avoid format string issues in template
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

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Calling LLM for news analysis...", total=None)
            result = _call_llm(user_prompt)
    else:
        print("Calling LLM for news analysis...")
        result = _call_llm(user_prompt)
    
    if result is None:
        return None
    
    return _parse_llm_response(result)


def _call_llm(user_prompt: str) -> Optional[str]:
    """Make the actual LLM API call."""
    try:
        output_chunks = replicate.run(
            "meta/meta-llama-3-70b-instruct",
            input={
                "prompt": user_prompt,
                "prompt_template": PROMPT_TEMPLATE,
                "temperature": 0.3,  # Lower for more consistent structured output
                "max_new_tokens": 500,
                "frequency_penalty": 0.1
            }
        )
        
        full_output = "".join(output_chunks)
        return full_output.strip()
        
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        return None


def _parse_llm_response(response: str) -> Optional[NewsAnalysis]:
    """Parse LLM response into structured NewsAnalysis."""
    try:
        # Find JSON object in response
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if not match:
            print(f"[ERROR] No JSON found in response: {response[:200]}")
            return None
        
        json_str = match.group(0)
        data = json.loads(json_str)
        
        # Create NewsAnalysis with validation
        analysis = NewsAnalysis(
            emotional_valence=float(data.get("emotional_valence", 0)),
            tension_level=float(data.get("tension_level", 0.5)),
            hope_factor=float(data.get("hope_factor", 0.5)),
            energy_level=str(data.get("energy_level", "medium")).lower(),
            dominant_themes=list(data.get("dominant_themes", []))[:5],
            summary=str(data.get("summary", "")),
            raw_response=response
        )
        
        # Clamp values to valid ranges
        analysis.emotional_valence = max(-1, min(1, analysis.emotional_valence))
        analysis.tension_level = max(0, min(1, analysis.tension_level))
        analysis.hope_factor = max(0, min(1, analysis.hope_factor))
        
        if analysis.energy_level not in ["low", "medium", "high"]:
            analysis.energy_level = "medium"
        
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error: {e}")
        print(f"[DEBUG] Response was: {response[:300]}")
        return None
    except Exception as e:
        print(f"[ERROR] Parse error: {e}")
        return None


# =============================================================================
# MOCK DATA FOR DRY-RUN MODE
# =============================================================================

MOCK_ANALYSES = {
    "positive": NewsAnalysis(
        emotional_valence=0.7,
        tension_level=0.2,
        hope_factor=0.8,
        energy_level="medium",
        dominant_themes=["science", "health", "environment", "diplomacy"],
        summary="A day of breakthroughs and hope, with major advances in climate action and medical research."
    ),
    "negative": NewsAnalysis(
        emotional_valence=-0.6,
        tension_level=0.8,
        hope_factor=0.2,
        energy_level="high",
        dominant_themes=["conflict", "disaster", "economy", "health"],
        summary="A difficult day marked by escalating tensions, natural disasters, and economic uncertainty."
    ),
    "mixed": NewsAnalysis(
        emotional_valence=0.1,
        tension_level=0.5,
        hope_factor=0.5,
        energy_level="medium",
        dominant_themes=["politics", "economy", "technology", "culture"],
        summary="A typical day with mixed developments - challenges balanced by community resilience and progress."
    ),
    "default": NewsAnalysis(
        emotional_valence=0.0,
        tension_level=0.4,
        hope_factor=0.5,
        energy_level="medium",
        dominant_themes=["general", "world"],
        summary="Standard news day with varied global developments."
    )
}


def get_mock_analysis(scenario: str = "default") -> NewsAnalysis:
    """Get mock analysis for dry-run mode."""
    return MOCK_ANALYSES.get(scenario, MOCK_ANALYSES["default"])


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_analysis(analysis: NewsAnalysis, headlines: List[str] = None):
    """Display analysis results with rich formatting."""
    
    if RICH_AVAILABLE:
        _visualize_rich(analysis, headlines)
    else:
        _visualize_basic(analysis, headlines)


def _visualize_rich(analysis: NewsAnalysis, headlines: List[str] = None):
    """Rich terminal visualization."""
    console.print()
    
    # Headlines panel (if provided)
    if headlines:
        headlines_text = "\n".join(headlines[:8])  # Show max 8
        if len(headlines) > 8:
            headlines_text += f"\n... and {len(headlines) - 8} more"
        console.print(Panel(headlines_text, title="[bold]Input Headlines[/bold]", border_style="dim"))
    
    # Main metrics table
    table = Table(title="News Mood Analysis", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="center")
    table.add_column("Visual", justify="left")
    
    # Emotional valence: -1 to +1
    valence = analysis.emotional_valence
    valence_bar = _make_bar(valence, -1, 1, center=True)
    valence_color = "red" if valence < -0.3 else "yellow" if valence < 0.3 else "green"
    table.add_row("Emotional Valence", f"[{valence_color}]{valence:+.2f}[/{valence_color}]", valence_bar)
    
    # Tension level: 0 to 1
    tension = analysis.tension_level
    tension_bar = _make_bar(tension, 0, 1)
    tension_color = "green" if tension < 0.3 else "yellow" if tension < 0.6 else "red"
    table.add_row("Tension Level", f"[{tension_color}]{tension:.2f}[/{tension_color}]", tension_bar)
    
    # Hope factor: 0 to 1
    hope = analysis.hope_factor
    hope_bar = _make_bar(hope, 0, 1)
    hope_color = "red" if hope < 0.3 else "yellow" if hope < 0.6 else "green"
    table.add_row("Hope Factor", f"[{hope_color}]{hope:.2f}[/{hope_color}]", hope_bar)
    
    # Energy level
    energy_colors = {"low": "blue", "medium": "yellow", "high": "red"}
    energy_color = energy_colors.get(analysis.energy_level, "white")
    table.add_row("Energy Level", f"[{energy_color}]{analysis.energy_level.upper()}[/{energy_color}]", "")
    
    console.print(table)
    
    # Themes
    themes_str = ", ".join(analysis.dominant_themes) if analysis.dominant_themes else "None detected"
    console.print(Panel(themes_str, title="[bold]Dominant Themes[/bold]", border_style="cyan"))
    
    # Summary
    console.print(Panel(analysis.summary, title="[bold]Summary[/bold]", border_style="green"))
    
    console.print()


def _make_bar(value: float, min_val: float, max_val: float, width: int = 20, center: bool = False) -> str:
    """Create a simple text-based bar visualization."""
    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0, min(1, normalized))
    
    if center:
        # For centered bars (like valence -1 to 1)
        mid = width // 2
        if value >= 0:
            filled = int(normalized * mid)
            bar = " " * mid + "|" + "=" * filled + " " * (mid - filled)
        else:
            filled = int((1 - normalized) * mid)
            bar = " " * (mid - filled) + "=" * filled + "|" + " " * mid
    else:
        filled = int(normalized * width)
        bar = "=" * filled + " " * (width - filled)
    
    return f"[{bar}]"


def _visualize_basic(analysis: NewsAnalysis, headlines: List[str] = None):
    """Basic terminal visualization without rich."""
    print()
    print("=" * 60)
    print("NEWS MOOD ANALYSIS")
    print("=" * 60)
    
    if headlines:
        print("\n--- Input Headlines ---")
        for h in headlines[:5]:
            print(h)
        if len(headlines) > 5:
            print(f"... and {len(headlines) - 5} more")
    
    print("\n--- Metrics ---")
    print(f"Emotional Valence: {analysis.emotional_valence:+.2f} (range: -1 to +1)")
    print(f"Tension Level:     {analysis.tension_level:.2f} (range: 0 to 1)")
    print(f"Hope Factor:       {analysis.hope_factor:.2f} (range: 0 to 1)")
    print(f"Energy Level:      {analysis.energy_level.upper()}")
    
    print("\n--- Dominant Themes ---")
    print(", ".join(analysis.dominant_themes) if analysis.dominant_themes else "None")
    
    print("\n--- Summary ---")
    print(analysis.summary)
    print()


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze news headlines for mood dimensions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 01_news_analyzer.py --scenario positive
  python 01_news_analyzer.py --scenario negative --dry-run
  python 01_news_analyzer.py --file ../../news_data_2026-01-07.json
        """
    )
    parser.add_argument("--file", "-f", type=str, help="Path to news JSON file")
    parser.add_argument("--scenario", "-s", type=str, 
                       choices=["positive", "negative", "mixed", "edge"],
                       default="mixed",
                       help="Test scenario to use (default: mixed)")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Skip LLM call, use mock data")
    parser.add_argument("--output", "-o", type=str, 
                       help="Save analysis to JSON file")
    
    args = parser.parse_args()
    
    # Determine input file
    if args.file:
        filepath = Path(args.file)
    else:
        filepath = get_test_data_path(args.scenario)
    
    if RICH_AVAILABLE:
        console.print(f"[bold]Loading news from:[/bold] {filepath}")
    else:
        print(f"Loading news from: {filepath}")
    
    # Load and process news
    try:
        articles = load_news_from_file(str(filepath))
        headlines = extract_headlines(articles)
        
        if not headlines:
            print("[ERROR] No headlines found in file")
            sys.exit(1)
        
        if RICH_AVAILABLE:
            console.print(f"[bold]Found {len(headlines)} headlines[/bold]")
        else:
            print(f"Found {len(headlines)} headlines")
        
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to load news: {e}")
        sys.exit(1)
    
    # Analyze
    if args.dry_run:
        if RICH_AVAILABLE:
            console.print("[yellow]DRY-RUN MODE: Using mock analysis[/yellow]")
        else:
            print("DRY-RUN MODE: Using mock analysis")
        analysis = get_mock_analysis(args.scenario)
    else:
        if not REPLICATE_AVAILABLE:
            print("[ERROR] replicate not available. Use --dry-run or install: pip install replicate")
            sys.exit(1)
        
        analysis = analyze_news_with_llm(headlines)
        
        if analysis is None:
            print("[ERROR] Analysis failed")
            sys.exit(1)
    
    # Validate
    if not analysis.validate():
        print("[WARNING] Analysis validation failed, results may be unreliable")
    
    # Visualize
    visualize_analysis(analysis, headlines)
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "source_file": str(filepath),
            "headline_count": len(headlines),
            "analysis": analysis.to_dict()
        }
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        if RICH_AVAILABLE:
            console.print(f"[green]Analysis saved to: {output_path}[/green]")
        else:
            print(f"Analysis saved to: {output_path}")
    
    # Return analysis for programmatic use
    return analysis


if __name__ == "__main__":
    main()
