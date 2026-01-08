"""
Enhanced Prompt Builder - Step 03 (Revised)

Combines three layers for varied, nuanced MusicGen prompts:
1. STRUCTURE (Archetype) - Base genre, core instruments, tempo range
2. COLOR (Theme Textures) - Timbral, movement, harmonic character
3. VARIETY (Daily Seed) - Controlled randomness for day-to-day freshness

Usage:
    python 03_prompt_builder.py --selection outputs/selection_mixed.json
    python 03_prompt_builder.py --scenario positive --dry-run
    python 03_prompt_builder.py --selection outputs/selection_mixed.json --themes technology conflict
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import date
import random

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from archetypes import (
    ArchetypeName,
    MusicDescriptor,
    ARCHETYPES,
    get_archetype,
)

from theme_textures import (
    blend_textures,
    DailyVariation,
    TextureBlend,
    get_texture,
    resolve_theme,
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


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PromptComponents:
    """Full breakdown of prompt components."""
    # Structure (from archetype)
    genre: str
    base_instruments: List[str]
    base_moods: List[str]
    base_tempo: int
    
    # Color (from theme textures)
    texture_timbre: List[str]
    texture_movement: List[str]
    texture_harmonic: List[str]
    
    # Variety (from daily seed)
    tempo_final: int
    instrument_variant: int
    
    # Metadata
    primary_archetype: str
    secondary_archetype: Optional[str]
    blend_ratio: Optional[float]
    intensity_level: str
    source_themes: List[str]
    date_seed: str


@dataclass 
class PromptResult:
    """Final prompt with all metadata."""
    prompt: str
    prompt_minimal: str
    prompt_natural: str
    components: PromptComponents
    
    def to_dict(self) -> Dict:
        return {
            "prompt": self.prompt,
            "prompt_minimal": self.prompt_minimal,
            "prompt_natural": self.prompt_natural,
            "components": {
                "genre": self.components.genre,
                "base_instruments": self.components.base_instruments,
                "base_moods": self.components.base_moods,
                "base_tempo": self.components.base_tempo,
                "texture_timbre": self.components.texture_timbre,
                "texture_movement": self.components.texture_movement,
                "texture_harmonic": self.components.texture_harmonic,
                "tempo_final": self.components.tempo_final,
                "instrument_variant": self.components.instrument_variant,
                "primary_archetype": self.components.primary_archetype,
                "secondary_archetype": self.components.secondary_archetype,
                "blend_ratio": self.components.blend_ratio,
                "intensity_level": self.components.intensity_level,
                "source_themes": self.components.source_themes,
                "date_seed": self.components.date_seed,
            }
        }


# =============================================================================
# INTENSITY MODIFIERS
# =============================================================================

INTENSITY_CONFIG = {
    "low": {
        "adjectives": ["soft", "gentle", "subtle", "delicate", "light"],
        "tempo_adjust": -3,
    },
    "medium": {
        "adjectives": ["warm", "flowing", "smooth", "balanced"],
        "tempo_adjust": 0,
    },
    "high": {
        "adjectives": ["deep", "rich", "layered", "evolving", "expansive"],
        "tempo_adjust": +3,
    },
}


# =============================================================================
# PROMPT BUILDING
# =============================================================================

def build_prompt(
    primary: ArchetypeName,
    secondary: Optional[ArchetypeName] = None,
    blend_ratio: Optional[float] = None,
    intensity_level: str = "medium",
    themes: List[str] = None,
    date_seed: date = None,
) -> PromptResult:
    """
    Build a nuanced MusicGen prompt combining structure, color, and variety.
    """
    if date_seed is None:
        date_seed = date.today()
    
    if themes is None:
        themes = []
    
    # Get archetype descriptors
    primary_desc = get_archetype(primary)
    secondary_desc = get_archetype(secondary) if secondary else None
    
    # Get daily variation
    daily_var = DailyVariation.from_date(date_seed)
    
    # Get theme textures
    texture_blend = blend_textures(themes, date_seed=date_seed) if themes else None
    
    # Get intensity config
    intensity = INTENSITY_CONFIG.get(intensity_level, INTENSITY_CONFIG["medium"])
    
    # =========================================================================
    # LAYER 1: STRUCTURE (from archetypes)
    # =========================================================================
    
    # Genre: always from primary
    genre = primary_desc.genre
    
    # Instruments: primary (2) + secondary (1 if exists)
    instruments = list(primary_desc.instruments[:2])
    if secondary_desc:
        for inst in secondary_desc.instruments:
            if inst not in instruments:
                instruments.append(inst)
                break
    
    # Apply instrument rotation for variety
    if len(instruments) > 1 and daily_var.instrument_rotation > 0:
        # Rotate which instrument comes first
        rotation = daily_var.instrument_rotation % len(instruments)
        instruments = instruments[rotation:] + instruments[:rotation]
    
    # Moods: primary (2) + secondary (1 if exists)
    # Combine mood_musical and mood_emotional
    moods = list(primary_desc.mood_musical[:1] + primary_desc.mood_emotional[:1])
    if secondary_desc:
        for mood in secondary_desc.mood_emotional:
            if mood not in moods:
                moods.append(mood)
                break
    
    # Shuffle moods based on daily seed for variety
    rng = random.Random(daily_var.mood_shuffle_seed)
    rng.shuffle(moods)
    
    # Tempo: blend if secondary exists
    base_tempo = primary_desc.tempo_value
    if secondary_desc and blend_ratio:
        base_tempo = int(
            base_tempo * blend_ratio + 
            secondary_desc.tempo_value * (1 - blend_ratio)
        )
    
    # Apply intensity adjustment
    tempo_adjusted = base_tempo + intensity["tempo_adjust"]
    
    # Apply daily nudge
    tempo_final = tempo_adjusted + daily_var.tempo_nudge
    
    # =========================================================================
    # LAYER 2: COLOR (from theme textures)
    # =========================================================================
    
    texture_timbre = []
    texture_movement = []
    texture_harmonic = []
    source_themes = []
    
    if texture_blend:
        texture_timbre = texture_blend.timbre_words
        texture_movement = texture_blend.movement_words
        texture_harmonic = texture_blend.harmonic_words
        source_themes = texture_blend.source_themes
        
        # Emphasize based on daily variation
        if daily_var.texture_emphasis == "timbre" and texture_timbre:
            # Add extra timbre word to instruments
            pass  # Will be applied in prompt assembly
        elif daily_var.texture_emphasis == "movement" and texture_movement:
            # Add movement word to moods
            if texture_movement[0] not in moods:
                moods.append(texture_movement[0])
        elif daily_var.texture_emphasis == "harmonic" and texture_harmonic:
            # Add harmonic hint to moods
            if texture_harmonic[0] not in moods:
                moods.append(texture_harmonic[0])
    
    # =========================================================================
    # LAYER 3: VARIETY (apply intensity adjectives)
    # =========================================================================
    
    # Add intensity adjective to first instrument if not already modified
    if instruments:
        first_inst = instruments[0]
        has_adjective = any(
            first_inst.lower().startswith(adj) 
            for adj in ["soft", "gentle", "warm", "deep", "ethereal", 
                       "atmospheric", "expressive", "subtle", "flowing"]
        )
        
        if not has_adjective:
            adj = intensity["adjectives"][daily_var.instrument_rotation % len(intensity["adjectives"])]
            instruments[0] = f"{adj} {first_inst}"
    
    # Add texture timbre to second instrument if available
    if len(instruments) > 1 and texture_timbre:
        second_inst = instruments[1]
        has_adjective = any(
            second_inst.lower().startswith(adj) 
            for adj in texture_timbre + ["soft", "gentle", "warm", "deep"]
        )
        
        if not has_adjective and texture_timbre:
            instruments[1] = f"{texture_timbre[0]} {second_inst}"
    
    # =========================================================================
    # BUILD COMPONENTS
    # =========================================================================
    
    components = PromptComponents(
        genre=genre,
        base_instruments=instruments,
        base_moods=moods[:4],  # Cap at 4 moods
        base_tempo=base_tempo,
        texture_timbre=texture_timbre,
        texture_movement=texture_movement,
        texture_harmonic=texture_harmonic,
        tempo_final=tempo_final,
        instrument_variant=daily_var.instrument_rotation,
        primary_archetype=primary.value,
        secondary_archetype=secondary.value if secondary else None,
        blend_ratio=blend_ratio,
        intensity_level=intensity_level,
        source_themes=source_themes,
        date_seed=date_seed.isoformat(),
    )
    
    # =========================================================================
    # ASSEMBLE PROMPTS (3 styles)
    # =========================================================================
    
    prompt_default = assemble_prompt_default(components)
    prompt_minimal = assemble_prompt_minimal(components)
    prompt_natural = assemble_prompt_natural(components)
    
    return PromptResult(
        prompt=prompt_default,
        prompt_minimal=prompt_minimal,
        prompt_natural=prompt_natural,
        components=components,
    )


# =============================================================================
# PROMPT ASSEMBLY FUNCTIONS
# =============================================================================

def get_tempo_descriptor(bpm: int) -> str:
    """Map BPM to descriptive tempo term."""
    if bpm < 55:
        return "very slow"
    elif bpm < 65:
        return "slow"
    elif bpm < 75:
        return "moderate"
    elif bpm < 90:
        return "medium"
    else:
        return "flowing"


def assemble_prompt_default(c: PromptComponents) -> str:
    """
    Default prompt style - balanced and descriptive.
    
    Pattern: "[genre] with [instruments], [moods], [tempo], [technical]"
    """
    parts = []
    
    # Genre (capitalize first letter)
    parts.append(c.genre.capitalize())
    
    # Instruments
    if c.base_instruments:
        if len(c.base_instruments) == 1:
            inst_str = c.base_instruments[0]
        elif len(c.base_instruments) == 2:
            inst_str = f"{c.base_instruments[0]} and {c.base_instruments[1]}"
        else:
            inst_str = ", ".join(c.base_instruments[:-1]) + f" and {c.base_instruments[-1]}"
        parts.append(f"with {inst_str}")
    
    # Moods (select best 2-3)
    if c.base_moods:
        # Deduplicate similar moods
        unique_moods = []
        for mood in c.base_moods:
            if not any(mood.lower() in m.lower() or m.lower() in mood.lower() 
                      for m in unique_moods):
                unique_moods.append(mood)
        
        mood_str = " and ".join(unique_moods[:2])
        if len(unique_moods) > 2:
            mood_str += f", {unique_moods[2]}"
        parts.append(mood_str)
    
    # Tempo
    tempo_desc = get_tempo_descriptor(c.tempo_final)
    parts.append(f"{tempo_desc} {c.tempo_final} BPM")
    
    # Technical
    technical = ["stereo"]
    if "ambient" in c.genre.lower():
        technical.append("spacious")
    parts.append(", ".join(technical))
    
    return ", ".join(parts)


def assemble_prompt_minimal(c: PromptComponents) -> str:
    """
    Minimal prompt - just essential keywords.
    Sometimes works better for MusicGen.
    """
    elements = [
        c.genre,
        c.base_instruments[0] if c.base_instruments else "",
        c.base_moods[0] if c.base_moods else "",
    ]
    
    # Add one texture word if available
    if c.texture_timbre:
        elements.append(c.texture_timbre[0])
    
    elements.extend([
        f"{c.tempo_final} BPM",
        "stereo"
    ])
    
    return ", ".join(e for e in elements if e)


def assemble_prompt_natural(c: PromptComponents) -> str:
    """
    Natural language prompt - more conversational.
    Can yield more cohesive, musical results.
    """
    mood_phrase = " and ".join(c.base_moods[:2]) if c.base_moods else "atmospheric"
    inst_phrase = " and ".join(c.base_instruments[:2]) if c.base_instruments else "synthesizers"
    tempo_desc = get_tempo_descriptor(c.tempo_final)
    
    # Add texture color if available
    texture_phrase = ""
    if c.texture_timbre:
        texture_phrase = f" with {c.texture_timbre[0]} textures"
    elif c.texture_movement:
        texture_phrase = f", {c.texture_movement[0]}"
    
    return (
        f"A {mood_phrase} piece of {c.genre} music{texture_phrase} "
        f"featuring {inst_phrase}, "
        f"at a {tempo_desc} {c.tempo_final} BPM tempo"
    )


# =============================================================================
# FILE I/O
# =============================================================================

def load_selection_from_file(filepath: str) -> dict:
    """Load selection JSON from file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_prompt(result: PromptResult, filepath: str):
    """Save prompt result to JSON file."""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_prompt(result: PromptResult):
    """Display prompt result with rich formatting."""
    if RICH_AVAILABLE:
        _visualize_rich(result)
    else:
        _visualize_basic(result)


def _visualize_rich(result: PromptResult):
    """Rich terminal visualization."""
    console.print()
    
    c = result.components
    
    # Three-layer breakdown
    table = Table(title="Prompt Composition", show_header=True, header_style="bold cyan")
    table.add_column("Layer", style="bold", width=12)
    table.add_column("Component", width=15)
    table.add_column("Value", width=45)
    
    # Structure layer
    table.add_row("[green]STRUCTURE[/green]", "Genre", c.genre)
    table.add_row("", "Instruments", " | ".join(c.base_instruments))
    table.add_row("", "Moods", " | ".join(c.base_moods))
    table.add_row("", "Base Tempo", f"{c.base_tempo} BPM")
    
    # Color layer
    table.add_row("[yellow]COLOR[/yellow]", "Themes", " → ".join(c.source_themes) if c.source_themes else "[dim]none[/dim]")
    table.add_row("", "Timbre", " | ".join(c.texture_timbre) if c.texture_timbre else "[dim]none[/dim]")
    table.add_row("", "Movement", " | ".join(c.texture_movement) if c.texture_movement else "[dim]none[/dim]")
    table.add_row("", "Harmonic", " | ".join(c.texture_harmonic) if c.texture_harmonic else "[dim]none[/dim]")
    
    # Variety layer
    table.add_row("[magenta]VARIETY[/magenta]", "Date Seed", c.date_seed)
    table.add_row("", "Final Tempo", f"{c.tempo_final} BPM")
    table.add_row("", "Intensity", c.intensity_level.upper())
    
    console.print(table)
    
    # Archetype info
    if c.secondary_archetype:
        blend_info = f"[bold]{c.primary_archetype}[/bold] ({c.blend_ratio:.0%}) + [bold]{c.secondary_archetype}[/bold] ({1-c.blend_ratio:.0%})"
    else:
        blend_info = f"[bold]{c.primary_archetype}[/bold] (100%)"
    
    console.print(Panel(blend_info, title="Archetype Blend", border_style="dim"))
    
    # All three prompt styles
    console.print(Panel(
        f"[bold green]{result.prompt}[/bold green]",
        title="[bold]🎵 Default Prompt[/bold]",
        border_style="green",
        padding=(1, 2)
    ))
    
    console.print(Panel(
        f"[cyan]{result.prompt_minimal}[/cyan]\n\n[yellow]{result.prompt_natural}[/yellow]",
        title="Alternative Styles (Minimal / Natural)",
        border_style="dim"
    ))
    
    console.print()


def _visualize_basic(result: PromptResult):
    """Basic terminal visualization."""
    print()
    print("=" * 70)
    print("PROMPT COMPOSITION")
    print("=" * 70)
    
    c = result.components
    
    print(f"\n[STRUCTURE]")
    print(f"  Genre: {c.genre}")
    print(f"  Instruments: {', '.join(c.base_instruments)}")
    print(f"  Moods: {', '.join(c.base_moods)}")
    print(f"  Base Tempo: {c.base_tempo} BPM")
    
    print(f"\n[COLOR]")
    print(f"  Themes: {', '.join(c.source_themes) if c.source_themes else 'none'}")
    print(f"  Timbre: {', '.join(c.texture_timbre) if c.texture_timbre else 'none'}")
    print(f"  Movement: {', '.join(c.texture_movement) if c.texture_movement else 'none'}")
    
    print(f"\n[VARIETY]")
    print(f"  Date: {c.date_seed}")
    print(f"  Final Tempo: {c.tempo_final} BPM")
    
    print("\n" + "-" * 70)
    print("DEFAULT PROMPT:")
    print("-" * 70)
    print(result.prompt)
    
    print("\n" + "-" * 70)
    print("MINIMAL:")
    print(result.prompt_minimal)
    print("\nNATURAL:")
    print(result.prompt_natural)
    print()


# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def build_prompt_from_selection(
    selection: dict,
    themes: List[str] = None,
    date_seed: date = None,
) -> PromptResult:
    """Build prompt from selection JSON (output of 02_archetype_selector.py)."""
    primary = ArchetypeName(selection["primary"])
    secondary = ArchetypeName(selection["secondary"]) if selection.get("secondary") else None
    blend_ratio = selection.get("blend_ratio")
    intensity_level = selection.get("intensity_level", "medium")
    
    return build_prompt(
        primary=primary,
        secondary=secondary,
        blend_ratio=blend_ratio,
        intensity_level=intensity_level,
        themes=themes or [],
        date_seed=date_seed,
    )


# =============================================================================
# MOCK DATA
# =============================================================================

MOCK_SELECTIONS = {
    "positive": {
        "primary": "tranquil_optimism",
        "secondary": "serene_resilience",
        "blend_ratio": 0.57,
        "intensity_level": "low",
    },
    "negative": {
        "primary": "melancholic_beauty",
        "secondary": None,
        "blend_ratio": None,
        "intensity_level": "high",
    },
    "mixed": {
        "primary": "cautious_hope",
        "secondary": "gentle_tension",
        "blend_ratio": 0.51,
        "intensity_level": "high",
    },
}

MOCK_THEMES = {
    "positive": ["science", "environment", "peace"],
    "negative": ["conflict", "economy", "health"],
    "mixed": ["politics", "economy", "technology"],
}


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build nuanced MusicGen prompts with theme textures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 03_prompt_builder.py --selection outputs/selection_mixed.json
  python 03_prompt_builder.py --selection outputs/selection_mixed.json --themes politics economy
  python 03_prompt_builder.py --scenario positive --dry-run
  python 03_prompt_builder.py --scenario mixed --date 2026-01-10
        """
    )
    parser.add_argument("--selection", "-s", type=str,
                       help="Path to selection JSON file")
    parser.add_argument("--scenario", type=str,
                       choices=["positive", "negative", "mixed"],
                       help="Use mock scenario")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Use mock data")
    parser.add_argument("--themes", "-t", nargs="+", type=str,
                       help="Theme keywords (e.g., technology conflict)")
    parser.add_argument("--date", type=str,
                       help="Date seed for variety (YYYY-MM-DD)")
    parser.add_argument("--output", "-o", type=str,
                       help="Save prompt to JSON file")
    
    args = parser.parse_args()
    
    # Parse date
    date_seed = None
    if args.date:
        from datetime import datetime
        date_seed = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        date_seed = date.today()
    
    # Determine input source
    selection = None
    themes = args.themes or []
    
    if args.selection:
        # Load from file
        try:
            selection = load_selection_from_file(args.selection)
            if RICH_AVAILABLE:
                console.print(f"[bold]Loaded selection from:[/bold] {args.selection}")
        except FileNotFoundError:
            print(f"[ERROR] File not found: {args.selection}")
            sys.exit(1)
    
    elif args.scenario or args.dry_run:
        # Use mock data
        scenario = args.scenario or "mixed"
        selection = MOCK_SELECTIONS.get(scenario, MOCK_SELECTIONS["mixed"])
        
        # Use mock themes if none specified
        if not themes:
            themes = MOCK_THEMES.get(scenario, [])
        
        if RICH_AVAILABLE:
            console.print(f"[yellow]Using mock scenario: {scenario}[/yellow]")
    
    else:
        # Default: try to load most recent selection
        outputs_dir = Path(__file__).parent / "outputs"
        selection_files = list(outputs_dir.glob("selection_*.json"))
        
        if selection_files:
            latest = max(selection_files, key=lambda p: p.stat().st_mtime)
            selection = load_selection_from_file(str(latest))
            if RICH_AVAILABLE:
                console.print(f"[bold]Loaded latest selection:[/bold] {latest.name}")
        else:
            print("[ERROR] No input specified. Use --selection or --scenario")
            parser.print_help()
            sys.exit(1)
    
    # Build prompt
    result = build_prompt_from_selection(selection, themes=themes, date_seed=date_seed)
    
    # Visualize
    visualize_prompt(result)
    
    # Save if requested
    if args.output:
        save_prompt(result, args.output)
        if RICH_AVAILABLE:
            console.print(f"[green]Prompt saved to: {args.output}[/green]")
    
    return result


if __name__ == "__main__":
    main()
