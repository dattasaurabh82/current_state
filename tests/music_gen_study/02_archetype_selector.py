"""
Archetype Selector Module - Step 02

Maps structured news analysis to mood archetypes using rule-based scoring.
Implements "Smart Medium" blending: primary archetype + compatible secondary.

Input: NewsAnalysis (from 01_news_analyzer.py)
Output: ArchetypeSelection with primary, optional secondary, and scores

Scoring Logic:
- Each archetype has an "ideal" profile (valence, tension, hope ranges)
- Score = how well the analysis matches that profile
- Secondary only selected if: compatible AND score >= 70% of primary

Usage:
    python 02_archetype_selector.py --analysis outputs/analysis_mixed.json
    python 02_archetype_selector.py --scenario positive --dry-run
    python 02_archetype_selector.py --interactive
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from archetypes import (
    ArchetypeName,
    MusicDescriptor,
    ARCHETYPES,
    COMPATIBILITY_MATRIX,
    get_archetype,
    get_compatible_archetypes,
    is_compatible,
    get_intensity_level,
)

# Try to import rich for nice terminal output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    print("[INFO] 'rich' not installed. Using basic output.")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class NewsAnalysis:
    """Input structure from news analyzer."""
    emotional_valence: float      # -1 to +1
    tension_level: float          # 0 to 1
    hope_factor: float            # 0 to 1
    energy_level: str             # "low", "medium", "high"
    dominant_themes: List[str]
    summary: str


@dataclass
class ArchetypeScore:
    """Score for a single archetype."""
    archetype: ArchetypeName
    score: float                  # 0 to 1
    valence_match: float          # Component scores for debugging
    tension_match: float
    hope_match: float
    energy_match: float


@dataclass
class ArchetypeSelection:
    """Final selection result."""
    primary: ArchetypeName
    primary_score: float
    secondary: Optional[ArchetypeName]
    secondary_score: Optional[float]
    all_scores: List[ArchetypeScore]
    intensity_level: str          # "low", "medium", "high"
    blend_ratio: Optional[float]  # e.g., 0.7 means 70% primary, 30% secondary
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "primary": self.primary.value,
            "primary_score": round(self.primary_score, 3),
            "secondary": self.secondary.value if self.secondary else None,
            "secondary_score": round(self.secondary_score, 3) if self.secondary_score else None,
            "intensity_level": self.intensity_level,
            "blend_ratio": self.blend_ratio,
            "all_scores": [
                {
                    "archetype": s.archetype.value,
                    "score": round(s.score, 3),
                    "components": {
                        "valence": round(s.valence_match, 3),
                        "tension": round(s.tension_match, 3),
                        "hope": round(s.hope_match, 3),
                        "energy": round(s.energy_match, 3)
                    }
                }
                for s in self.all_scores
            ]
        }


# =============================================================================
# ARCHETYPE PROFILES
# =============================================================================
# Each archetype has an "ideal" profile - the analysis values it best matches.
# These are defined as (center, tolerance) tuples.
# Score = 1.0 when analysis == center, decreasing as distance increases.
# =============================================================================

@dataclass
class ArchetypeProfile:
    """Ideal analysis profile for an archetype."""
    valence_center: float         # Ideal emotional_valence
    valence_tolerance: float      # How much deviation is acceptable
    tension_center: float         # Ideal tension_level
    tension_tolerance: float
    hope_center: float            # Ideal hope_factor
    hope_tolerance: float
    preferred_energy: List[str]   # Acceptable energy levels


ARCHETYPE_PROFILES: Dict[ArchetypeName, ArchetypeProfile] = {
    
    # Tranquil Optimism: Positive, low tension, high hope, calm energy
    ArchetypeName.TRANQUIL_OPTIMISM: ArchetypeProfile(
        valence_center=0.6,
        valence_tolerance=0.4,
        tension_center=0.2,
        tension_tolerance=0.3,
        hope_center=0.8,
        hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    
    # Reflective Calm: Neutral-positive, low tension, moderate hope, low energy
    ArchetypeName.REFLECTIVE_CALM: ArchetypeProfile(
        valence_center=0.2,
        valence_tolerance=0.4,
        tension_center=0.2,
        tension_tolerance=0.3,
        hope_center=0.5,
        hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    
    # Gentle Tension: Slightly negative, moderate-high tension, moderate hope
    ArchetypeName.GENTLE_TENSION: ArchetypeProfile(
        valence_center=-0.1,
        valence_tolerance=0.4,
        tension_center=0.6,
        tension_tolerance=0.3,
        hope_center=0.4,
        hope_tolerance=0.3,
        preferred_energy=["medium", "high"]
    ),
    
    # Melancholic Beauty: Negative, moderate tension, low hope, low-medium energy
    ArchetypeName.MELANCHOLIC_BEAUTY: ArchetypeProfile(
        valence_center=-0.4,
        valence_tolerance=0.4,
        tension_center=0.5,
        tension_tolerance=0.3,
        hope_center=0.3,
        hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    
    # Cautious Hope: Slightly positive, moderate tension, moderate-high hope
    ArchetypeName.CAUTIOUS_HOPE: ArchetypeProfile(
        valence_center=0.2,
        valence_tolerance=0.4,
        tension_center=0.5,
        tension_tolerance=0.3,
        hope_center=0.6,
        hope_tolerance=0.3,
        preferred_energy=["medium"]
    ),
    
    # Serene Resilience: Positive, moderate tension, high hope, medium energy
    ArchetypeName.SERENE_RESILIENCE: ArchetypeProfile(
        valence_center=0.3,
        valence_tolerance=0.4,
        tension_center=0.4,
        tension_tolerance=0.3,
        hope_center=0.7,
        hope_tolerance=0.3,
        preferred_energy=["medium", "high"]
    ),
}


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_dimension_match(value: float, center: float, tolerance: float) -> float:
    """
    Calculate how well a value matches a target center with given tolerance.
    
    Returns 1.0 when value == center, decreasing linearly to 0 at edges.
    Uses a Gaussian-like falloff for smoother transitions.
    """
    distance = abs(value - center)
    
    # Normalize distance by tolerance
    normalized_distance = distance / tolerance if tolerance > 0 else distance
    
    # Gaussian-like falloff: score = exp(-distance^2)
    # But clamp to [0, 1] range
    import math
    score = math.exp(-normalized_distance ** 2)
    
    return max(0.0, min(1.0, score))


def calculate_energy_match(energy: str, preferred: List[str]) -> float:
    """Calculate energy level match."""
    if energy in preferred:
        return 1.0
    else:
        # Partial credit for adjacent energy levels
        energy_order = ["low", "medium", "high"]
        if energy not in energy_order:
            return 0.5  # Unknown energy, neutral score
        
        energy_idx = energy_order.index(energy)
        
        # Check distance to nearest preferred
        min_distance = float('inf')
        for pref in preferred:
            if pref in energy_order:
                pref_idx = energy_order.index(pref)
                min_distance = min(min_distance, abs(energy_idx - pref_idx))
        
        if min_distance == 1:
            return 0.6  # Adjacent
        elif min_distance == 2:
            return 0.3  # Far
        else:
            return 0.5  # Default


def score_archetype(analysis: NewsAnalysis, archetype: ArchetypeName) -> ArchetypeScore:
    """
    Score how well an analysis matches an archetype profile.
    
    Returns ArchetypeScore with overall score and component breakdowns.
    """
    profile = ARCHETYPE_PROFILES[archetype]
    
    # Calculate component matches
    valence_match = calculate_dimension_match(
        analysis.emotional_valence,
        profile.valence_center,
        profile.valence_tolerance
    )
    
    tension_match = calculate_dimension_match(
        analysis.tension_level,
        profile.tension_center,
        profile.tension_tolerance
    )
    
    hope_match = calculate_dimension_match(
        analysis.hope_factor,
        profile.hope_center,
        profile.hope_tolerance
    )
    
    energy_match = calculate_energy_match(
        analysis.energy_level,
        profile.preferred_energy
    )
    
    # Weighted combination
    # Valence and hope are most important for mood, tension adds nuance
    weights = {
        "valence": 0.30,
        "tension": 0.25,
        "hope": 0.30,
        "energy": 0.15
    }
    
    overall_score = (
        weights["valence"] * valence_match +
        weights["tension"] * tension_match +
        weights["hope"] * hope_match +
        weights["energy"] * energy_match
    )
    
    return ArchetypeScore(
        archetype=archetype,
        score=overall_score,
        valence_match=valence_match,
        tension_match=tension_match,
        hope_match=hope_match,
        energy_match=energy_match
    )


def score_all_archetypes(analysis: NewsAnalysis) -> List[ArchetypeScore]:
    """Score all archetypes and return sorted list (highest first)."""
    scores = [
        score_archetype(analysis, archetype)
        for archetype in ArchetypeName
    ]
    
    # Sort by score descending
    scores.sort(key=lambda s: s.score, reverse=True)
    
    return scores


# =============================================================================
# SELECTION LOGIC
# =============================================================================

# Minimum ratio of secondary score to primary score for blending
SECONDARY_THRESHOLD_RATIO = 0.70

# Minimum absolute score for secondary to be considered
SECONDARY_MIN_SCORE = 0.50


def select_archetypes(analysis: NewsAnalysis) -> ArchetypeSelection:
    """
    Select primary and optional secondary archetype based on analysis.
    
    Rules:
    1. Primary = highest scoring archetype
    2. Secondary = second highest IF:
       - It's compatible with primary (per COMPATIBILITY_MATRIX)
       - Its score >= SECONDARY_THRESHOLD_RATIO * primary score
       - Its score >= SECONDARY_MIN_SCORE
    3. Blend ratio based on relative scores
    """
    # Score all archetypes
    all_scores = score_all_archetypes(analysis)
    
    # Primary is always the top scorer
    primary_score = all_scores[0]
    primary = primary_score.archetype
    
    # Look for compatible secondary
    secondary = None
    secondary_score_obj = None
    blend_ratio = None
    
    for candidate in all_scores[1:]:
        # Check compatibility
        if not is_compatible(primary, candidate.archetype):
            continue
        
        # Check score thresholds
        ratio = candidate.score / primary_score.score if primary_score.score > 0 else 0
        
        if ratio >= SECONDARY_THRESHOLD_RATIO and candidate.score >= SECONDARY_MIN_SCORE:
            secondary = candidate.archetype
            secondary_score_obj = candidate
            
            # Calculate blend ratio: primary gets proportionally more
            # If scores are equal, blend is 50/50
            # If primary is much higher, blend approaches 100/0
            total = primary_score.score + candidate.score
            blend_ratio = primary_score.score / total if total > 0 else 1.0
            
            break  # Take first compatible secondary
    
    # Determine intensity level from tension
    intensity_level = get_intensity_level(analysis.tension_level)
    
    return ArchetypeSelection(
        primary=primary,
        primary_score=primary_score.score,
        secondary=secondary,
        secondary_score=secondary_score_obj.score if secondary_score_obj else None,
        all_scores=all_scores,
        intensity_level=intensity_level,
        blend_ratio=round(blend_ratio, 2) if blend_ratio else None
    )


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_selection(selection: ArchetypeSelection, analysis: NewsAnalysis = None):
    """Display selection results with rich formatting."""
    
    if RICH_AVAILABLE:
        _visualize_rich(selection, analysis)
    else:
        _visualize_basic(selection, analysis)


def _visualize_rich(selection: ArchetypeSelection, analysis: NewsAnalysis = None):
    """Rich terminal visualization."""
    console.print()
    
    # Input analysis summary (if provided)
    if analysis:
        analysis_text = (
            f"Valence: {analysis.emotional_valence:+.2f}  |  "
            f"Tension: {analysis.tension_level:.2f}  |  "
            f"Hope: {analysis.hope_factor:.2f}  |  "
            f"Energy: {analysis.energy_level.upper()}"
        )
        console.print(Panel(analysis_text, title="[bold]Input Analysis[/bold]", border_style="dim"))
    
    # Scoring table
    table = Table(title="Archetype Scores", show_header=True, header_style="bold cyan")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("Archetype", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Bar", justify="left", width=20)
    table.add_column("V", justify="right", width=5)  # Valence
    table.add_column("T", justify="right", width=5)  # Tension
    table.add_column("H", justify="right", width=5)  # Hope
    table.add_column("E", justify="right", width=5)  # Energy
    table.add_column("Status", justify="center")
    
    for i, score in enumerate(selection.all_scores):
        rank = str(i + 1)
        name = score.archetype.value.replace("_", " ").title()
        score_val = f"{score.score:.3f}"
        
        # Score bar
        bar_width = int(score.score * 15)
        bar = "=" * bar_width + " " * (15 - bar_width)
        
        # Component scores
        v = f"{score.valence_match:.2f}"
        t = f"{score.tension_match:.2f}"
        h = f"{score.hope_match:.2f}"
        e = f"{score.energy_match:.2f}"
        
        # Status indicator
        if score.archetype == selection.primary:
            status = "[bold green]PRIMARY[/bold green]"
            row_style = "green"
        elif score.archetype == selection.secondary:
            status = "[bold yellow]SECONDARY[/bold yellow]"
            row_style = "yellow"
        elif is_compatible(selection.primary, score.archetype):
            status = "[dim]compatible[/dim]"
            row_style = None
        else:
            status = "[dim red]--[/dim red]"
            row_style = "dim"
        
        table.add_row(rank, name, score_val, f"[{bar}]", v, t, h, e, status, style=row_style)
    
    console.print(table)
    console.print("[dim]V=Valence T=Tension H=Hope E=Energy[/dim]")
    
    # Selection result panel
    result_lines = []
    
    primary_desc = get_archetype(selection.primary)
    result_lines.append(f"[bold green]Primary:[/bold green] {selection.primary.value.replace('_', ' ').title()}")
    result_lines.append(f"  Genre: {primary_desc.genre}")
    result_lines.append(f"  Score: {selection.primary_score:.3f}")
    
    if selection.secondary:
        secondary_desc = get_archetype(selection.secondary)
        result_lines.append("")
        result_lines.append(f"[bold yellow]Secondary:[/bold yellow] {selection.secondary.value.replace('_', ' ').title()}")
        result_lines.append(f"  Genre: {secondary_desc.genre}")
        result_lines.append(f"  Score: {selection.secondary_score:.3f}")
        result_lines.append(f"  Blend: {selection.blend_ratio:.0%} / {1-selection.blend_ratio:.0%}")
    else:
        result_lines.append("")
        result_lines.append("[dim]No compatible secondary selected[/dim]")
    
    result_lines.append("")
    result_lines.append(f"[bold]Intensity Level:[/bold] {selection.intensity_level.upper()}")
    
    console.print(Panel("\n".join(result_lines), title="[bold]Selection Result[/bold]", border_style="green"))
    console.print()


def _visualize_basic(selection: ArchetypeSelection, analysis: NewsAnalysis = None):
    """Basic terminal visualization without rich."""
    print()
    print("=" * 60)
    print("ARCHETYPE SELECTION")
    print("=" * 60)
    
    if analysis:
        print(f"\nInput: Valence={analysis.emotional_valence:+.2f}, "
              f"Tension={analysis.tension_level:.2f}, "
              f"Hope={analysis.hope_factor:.2f}, "
              f"Energy={analysis.energy_level}")
    
    print("\n--- Scores ---")
    for i, score in enumerate(selection.all_scores):
        marker = ""
        if score.archetype == selection.primary:
            marker = " <-- PRIMARY"
        elif score.archetype == selection.secondary:
            marker = " <-- SECONDARY"
        
        print(f"{i+1}. {score.archetype.value}: {score.score:.3f}{marker}")
    
    print("\n--- Selection ---")
    print(f"Primary: {selection.primary.value} (score: {selection.primary_score:.3f})")
    if selection.secondary:
        print(f"Secondary: {selection.secondary.value} (score: {selection.secondary_score:.3f})")
        print(f"Blend Ratio: {selection.blend_ratio:.0%} / {1-selection.blend_ratio:.0%}")
    else:
        print("Secondary: None")
    print(f"Intensity: {selection.intensity_level}")
    print()


# =============================================================================
# FILE I/O
# =============================================================================

def load_analysis_from_file(filepath: str) -> NewsAnalysis:
    """Load NewsAnalysis from JSON file (output of 01_news_analyzer.py)."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Handle wrapped format (from analyzer output)
    if "analysis" in data:
        analysis_data = data["analysis"]
    else:
        analysis_data = data
    
    return NewsAnalysis(
        emotional_valence=float(analysis_data["emotional_valence"]),
        tension_level=float(analysis_data["tension_level"]),
        hope_factor=float(analysis_data["hope_factor"]),
        energy_level=str(analysis_data["energy_level"]).lower(),
        dominant_themes=list(analysis_data.get("dominant_themes", [])),
        summary=str(analysis_data.get("summary", ""))
    )


def save_selection(selection: ArchetypeSelection, filepath: str):
    """Save selection to JSON file."""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(selection.to_dict(), f, indent=2)


# =============================================================================
# MOCK DATA FOR DRY-RUN
# =============================================================================

MOCK_ANALYSES = {
    "positive": NewsAnalysis(
        emotional_valence=0.7,
        tension_level=0.2,
        hope_factor=0.8,
        energy_level="high",
        dominant_themes=["environment", "science", "politics"],
        summary="A highly positive day marked by historic agreements and breakthroughs."
    ),
    "negative": NewsAnalysis(
        emotional_valence=-0.7,
        tension_level=0.9,
        hope_factor=0.2,
        energy_level="high",
        dominant_themes=["conflict", "economy", "health"],
        summary="A day of heightened tension and crisis."
    ),
    "mixed": NewsAnalysis(
        emotional_valence=0.1,
        tension_level=0.6,
        hope_factor=0.5,
        energy_level="medium",
        dominant_themes=["economy", "politics", "science"],
        summary="A day of mixed emotions with uncertainty and hope."
    ),
}


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Select mood archetypes based on news analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 02_archetype_selector.py --analysis outputs/analysis_mixed.json
  python 02_archetype_selector.py --scenario positive --dry-run
  python 02_archetype_selector.py --interactive
        """
    )
    parser.add_argument("--analysis", "-a", type=str, 
                       help="Path to analysis JSON file (from 01_news_analyzer.py)")
    parser.add_argument("--scenario", "-s", type=str,
                       choices=["positive", "negative", "mixed"],
                       help="Use mock scenario (for testing)")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Use mock data (requires --scenario)")
    parser.add_argument("--output", "-o", type=str,
                       help="Save selection to JSON file")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Enter analysis values interactively")
    
    args = parser.parse_args()
    
    # Determine input source
    analysis = None
    
    if args.interactive:
        # Interactive mode
        print("Enter analysis values:")
        try:
            valence = float(input("  Emotional valence (-1 to +1): "))
            tension = float(input("  Tension level (0 to 1): "))
            hope = float(input("  Hope factor (0 to 1): "))
            energy = input("  Energy level (low/medium/high): ").strip().lower()
            
            analysis = NewsAnalysis(
                emotional_valence=valence,
                tension_level=tension,
                hope_factor=hope,
                energy_level=energy,
                dominant_themes=[],
                summary="Interactive input"
            )
        except (ValueError, EOFError) as e:
            print(f"[ERROR] Invalid input: {e}")
            sys.exit(1)
    
    elif args.analysis:
        # Load from file
        try:
            analysis = load_analysis_from_file(args.analysis)
            if RICH_AVAILABLE:
                console.print(f"[bold]Loaded analysis from:[/bold] {args.analysis}")
            else:
                print(f"Loaded analysis from: {args.analysis}")
        except FileNotFoundError:
            print(f"[ERROR] File not found: {args.analysis}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to load analysis: {e}")
            sys.exit(1)
    
    elif args.scenario or args.dry_run:
        # Use mock data
        scenario = args.scenario or "mixed"
        analysis = MOCK_ANALYSES.get(scenario, MOCK_ANALYSES["mixed"])
        if RICH_AVAILABLE:
            console.print(f"[yellow]Using mock scenario: {scenario}[/yellow]")
        else:
            print(f"Using mock scenario: {scenario}")
    
    else:
        # Default: try to load most recent analysis
        outputs_dir = Path(__file__).parent / "outputs"
        analysis_files = list(outputs_dir.glob("analysis_*.json"))
        
        if analysis_files:
            latest = max(analysis_files, key=lambda p: p.stat().st_mtime)
            analysis = load_analysis_from_file(str(latest))
            if RICH_AVAILABLE:
                console.print(f"[bold]Loaded latest analysis:[/bold] {latest.name}")
            else:
                print(f"Loaded latest analysis: {latest.name}")
        else:
            print("[ERROR] No input specified. Use --analysis, --scenario, or --interactive")
            parser.print_help()
            sys.exit(1)
    
    # Select archetypes
    selection = select_archetypes(analysis)
    
    # Visualize
    visualize_selection(selection, analysis)
    
    # Save if requested
    if args.output:
        save_selection(selection, args.output)
        if RICH_AVAILABLE:
            console.print(f"[green]Selection saved to: {args.output}[/green]")
        else:
            print(f"Selection saved to: {args.output}")
    
    return selection


if __name__ == "__main__":
    main()
