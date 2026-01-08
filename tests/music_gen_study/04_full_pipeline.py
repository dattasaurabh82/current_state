"""
Full Pipeline - News to MusicGen Prompt (Enhanced)

Chains all steps together with theme textures and visualizations:
1. News Analysis (LLM) → structured dimensions + themes
2. Archetype Selection (rule-based) → primary/secondary archetypes  
3. Theme Textures → timbral/movement/harmonic color
4. Prompt Building (curated descriptors + daily variety) → MusicGen prompt
5. Visualizations → SVG charts

Usage:
    # Full pipeline with real news
    python 04_full_pipeline.py --news ../../news_data_2026-01-07.json
    
    # Full pipeline with test scenario
    python 04_full_pipeline.py --scenario mixed
    
    # Dry run (no LLM call)
    python 04_full_pipeline.py --scenario mixed --dry-run
    
    # Save all outputs including visualizations
    python 04_full_pipeline.py --news ../../news_data_2026-01-07.json --output-dir outputs/pipeline_run
"""

import json
import sys
import argparse
import importlib.util
from pathlib import Path
from datetime import datetime, date
from typing import Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import our modules directly
from archetypes import ArchetypeName, get_archetype

# Try to import rich
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
# MODULE LOADING HELPERS
# =============================================================================

def load_module(name: str, path: Path):
    """Dynamically load a module from path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

def run_pipeline(
    news_file: Optional[str] = None,
    scenario: Optional[str] = None,
    dry_run: bool = False,
    output_dir: Optional[str] = None,
    date_override: Optional[date] = None,
) -> dict:
    """
    Run the full news-to-prompt pipeline with theme textures and visualizations.
    
    Returns dict with all intermediate results.
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "input_source": news_file or f"scenario:{scenario}",
        "dry_run": dry_run,
        "date_seed": (date_override or date.today()).isoformat(),
    }
    
    base_path = Path(__file__).parent
    
    # =========================================================================
    # STEP 1: NEWS ANALYSIS
    # =========================================================================
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]━━━ STEP 1: News Analysis ━━━[/bold cyan]")
    else:
        print("\n=== STEP 1: News Analysis ===")
    
    # Load analyzer module
    news_analyzer = load_module("news_analyzer", base_path / "01_news_analyzer.py")
    
    # Load headlines
    if news_file:
        articles = news_analyzer.load_news_from_file(news_file)
        headlines = news_analyzer.extract_headlines(articles)
    elif scenario:
        test_data_dir = base_path / "test_data"
        scenario_file = test_data_dir / f"news_{scenario}.json"
        articles = news_analyzer.load_news_from_file(str(scenario_file))
        headlines = news_analyzer.extract_headlines(articles)
    else:
        headlines = []
    
    if not headlines:
        print("[ERROR] No headlines loaded")
        return results
    
    # Analyze
    if dry_run:
        analysis = news_analyzer.get_mock_analysis(scenario or "mixed")
        if RICH_AVAILABLE:
            console.print("[yellow]Using mock analysis (dry-run)[/yellow]")
    else:
        analysis = news_analyzer.analyze_news_with_llm(headlines)
    
    if not analysis:
        print("[ERROR] Analysis failed")
        return results
    
    results["analysis"] = {
        "emotional_valence": analysis.emotional_valence,
        "tension_level": analysis.tension_level,
        "hope_factor": analysis.hope_factor,
        "energy_level": analysis.energy_level,
        "dominant_themes": analysis.dominant_themes,
        "summary": analysis.summary,
    }
    
    # Visualize analysis
    news_analyzer.visualize_analysis(analysis, headlines)
    
    # =========================================================================
    # STEP 2: ARCHETYPE SELECTION
    # =========================================================================
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]━━━ STEP 2: Archetype Selection ━━━[/bold cyan]")
    else:
        print("\n=== STEP 2: Archetype Selection ===")
    
    # Load selector module
    archetype_selector = load_module("archetype_selector", base_path / "02_archetype_selector.py")
    
    # Convert analysis to selector format
    selector_analysis = archetype_selector.NewsAnalysis(
        emotional_valence=analysis.emotional_valence,
        tension_level=analysis.tension_level,
        hope_factor=analysis.hope_factor,
        energy_level=analysis.energy_level,
        dominant_themes=analysis.dominant_themes,
        summary=analysis.summary,
    )
    
    # Select archetypes
    selection = archetype_selector.select_archetypes(selector_analysis)
    
    results["selection"] = selection.to_dict()
    
    # Visualize selection
    archetype_selector.visualize_selection(selection, selector_analysis)
    
    # =========================================================================
    # STEP 3: THEME TEXTURES
    # =========================================================================
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]━━━ STEP 3: Theme Textures ━━━[/bold cyan]")
    else:
        print("\n=== STEP 3: Theme Textures ===")
    
    # Load theme textures module
    from theme_textures import blend_textures, DailyVariation
    
    themes = analysis.dominant_themes
    date_seed = date_override or date.today()
    
    # Get texture blend
    texture_blend = blend_textures(themes, date_seed=date_seed)
    daily_var = DailyVariation.from_date(date_seed)
    
    if RICH_AVAILABLE:
        texture_table = Table(title="Theme Texture Blend", show_header=True, header_style="bold yellow")
        texture_table.add_column("Category", style="bold", width=12)
        texture_table.add_column("Values", width=50)
        
        texture_table.add_row("Themes", " → ".join(texture_blend.source_themes))
        texture_table.add_row("Timbre", " | ".join(texture_blend.timbre_words) or "[dim]none[/dim]")
        texture_table.add_row("Movement", " | ".join(texture_blend.movement_words) or "[dim]none[/dim]")
        texture_table.add_row("Harmonic", " | ".join(texture_blend.harmonic_words) or "[dim]none[/dim]")
        
        console.print(texture_table)
        
        console.print(Panel(
            f"Date Seed: {date_seed}\n"
            f"Instrument Rotation: {daily_var.instrument_rotation}\n"
            f"Texture Emphasis: {daily_var.texture_emphasis}\n"
            f"Tempo Nudge: {daily_var.tempo_nudge:+d} BPM",
            title="Daily Variation",
            border_style="dim"
        ))
    else:
        print(f"Themes: {', '.join(texture_blend.source_themes)}")
        print(f"Timbre: {', '.join(texture_blend.timbre_words)}")
        print(f"Movement: {', '.join(texture_blend.movement_words)}")
        print(f"Harmonic: {', '.join(texture_blend.harmonic_words)}")
    
    results["theme_textures"] = {
        "source_themes": texture_blend.source_themes,
        "timbre": texture_blend.timbre_words,
        "movement": texture_blend.movement_words,
        "harmonic": texture_blend.harmonic_words,
        "daily_variation": {
            "instrument_rotation": daily_var.instrument_rotation,
            "texture_emphasis": daily_var.texture_emphasis,
            "tempo_nudge": daily_var.tempo_nudge,
        }
    }
    
    # =========================================================================
    # STEP 4: PROMPT BUILDING
    # =========================================================================
    if RICH_AVAILABLE:
        console.print("\n[bold cyan]━━━ STEP 4: Prompt Building ━━━[/bold cyan]")
    else:
        print("\n=== STEP 4: Prompt Building ===")
    
    # Load prompt builder module
    prompt_builder = load_module("prompt_builder", base_path / "03_prompt_builder.py")
    
    # Build prompt with theme textures
    prompt_result = prompt_builder.build_prompt_from_selection(
        selection=selection.to_dict(),
        themes=themes,
        date_seed=date_seed,
    )
    
    results["prompt"] = prompt_result.to_dict()
    
    # Visualize prompt
    prompt_builder.visualize_prompt(prompt_result)
    
    # =========================================================================
    # STEP 5: VISUALIZATIONS (if output dir specified)
    # =========================================================================
    if output_dir:
        if RICH_AVAILABLE:
            console.print("\n[bold cyan]━━━ STEP 5: Generating Visualizations ━━━[/bold cyan]")
        else:
            print("\n=== STEP 5: Generating Visualizations ===")
        
        from visualizations import generate_all_visualizations
        
        viz_dir = Path(output_dir) / "visualizations"
        
        viz_files = generate_all_visualizations(
            analysis=results["analysis"],
            selection=results["selection"],
            prompt_components=prompt_result.components.__dict__,
            output_dir=str(viz_dir),
            date_str=date_seed.isoformat(),
        )
        
        results["visualizations"] = viz_files
        
        if RICH_AVAILABLE:
            console.print(f"[green]Generated {len(viz_files)} SVG visualizations[/green]")
            for f in viz_files:
                console.print(f"  • {Path(f).name}")
        else:
            print(f"Generated {len(viz_files)} visualizations")
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    if RICH_AVAILABLE:
        console.print("\n[bold green]━━━ PIPELINE COMPLETE ━━━[/bold green]")
        
        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column("Label", style="bold")
        summary_table.add_column("Value")
        
        summary_table.add_row("Input", results["input_source"])
        summary_table.add_row("Headlines", str(len(headlines)))
        summary_table.add_row("Date Seed", results["date_seed"])
        summary_table.add_row("Valence", f"{analysis.emotional_valence:+.2f}")
        summary_table.add_row("Themes", ", ".join(themes[:3]))
        summary_table.add_row("Primary", selection.primary.value)
        summary_table.add_row("Secondary", selection.secondary.value if selection.secondary else "None")
        
        console.print(Panel(summary_table, title="Summary", border_style="green"))
        
        console.print(Panel(
            f"[bold green]{prompt_result.prompt}[/bold green]\n\n"
            f"[dim]Minimal: {prompt_result.prompt_minimal}[/dim]",
            title="🎵 Final Prompts",
            border_style="green",
            padding=(1, 2)
        ))
    else:
        print("\n=== PIPELINE COMPLETE ===")
        print(f"Input: {results['input_source']}")
        print(f"Headlines: {len(headlines)}")
        print(f"Primary: {selection.primary.value}")
        print(f"\nPrompt: {prompt_result.prompt}")
    
    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        # Save full results
        results_file = out_path / "pipeline_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save just the prompts (for easy access)
        prompt_file = out_path / "prompt.txt"
        with open(prompt_file, 'w') as f:
            f.write(f"DEFAULT:\n{prompt_result.prompt}\n\n")
            f.write(f"MINIMAL:\n{prompt_result.prompt_minimal}\n\n")
            f.write(f"NATURAL:\n{prompt_result.prompt_natural}\n")
        
        if RICH_AVAILABLE:
            console.print(f"\n[green]All outputs saved to: {output_dir}/[/green]")
        else:
            print(f"\nResults saved to: {output_dir}/")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Run full news-to-MusicGen-prompt pipeline with visualizations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 04_full_pipeline.py --news ../../news_data_2026-01-07.json
  python 04_full_pipeline.py --scenario positive --dry-run
  python 04_full_pipeline.py --scenario mixed --output-dir outputs/test_run
  python 04_full_pipeline.py --scenario mixed --date 2026-01-10  # Test date variation
        """
    )
    parser.add_argument("--news", "-n", type=str,
                       help="Path to news JSON file")
    parser.add_argument("--scenario", "-s", type=str,
                       choices=["positive", "negative", "mixed"],
                       help="Use test scenario")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Use mock LLM analysis")
    parser.add_argument("--output-dir", "-o", type=str,
                       help="Directory to save all outputs")
    parser.add_argument("--date", type=str,
                       help="Date seed for daily variation (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.news and not args.scenario:
        print("[ERROR] Specify --news or --scenario")
        parser.print_help()
        sys.exit(1)
    
    # Parse date
    date_override = None
    if args.date:
        date_override = datetime.strptime(args.date, "%Y-%m-%d").date()
    
    # Run pipeline
    results = run_pipeline(
        news_file=args.news,
        scenario=args.scenario,
        dry_run=args.dry_run,
        output_dir=args.output_dir,
        date_override=date_override,
    )
    
    return results


if __name__ == "__main__":
    main()
