"""
Music Generation - Step 04

Generate actual music using MusicGen via Replicate API.
Tests the quality and differentiation of our generated prompts.

Uses the same API pattern as lib/music_generator.py in the main project.

Usage:
    # Generate from a specific run
    python 04_generate_music.py --run run_positive
    
    # Generate from all runs
    python 04_generate_music.py --all
    
    # Generate from custom prompt
    python 04_generate_music.py --prompt "ambient electronic, soft pads, peaceful, 70 BPM"
    
    # Use minimal prompt style
    python 04_generate_music.py --run run_mixed --style minimal
"""

import json
import os
import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env from project root
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Strip whitespace/quotes from the Replicate API token
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token.strip().strip('"')

# Try to import replicate
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False
    print("[ERROR] replicate not installed. Run: pip install replicate")

# Try to import rich
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


# =============================================================================
# MUSICGEN CONFIGURATION (matching lib/music_generator.py)
# =============================================================================

# Same model as main project
MUSICGEN_MODEL = "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"

# Global for cancellation support
current_prediction = None


# =============================================================================
# MUSIC GENERATION (matching lib/music_generator.py pattern)
# =============================================================================

def generate_music(prompt: str, output_path: str, duration: int = 30) -> bool:
    """
    Generate music using MusicGen via Replicate API.
    
    Uses replicate.predictions.create() + wait() pattern for cancellation support.
    Matches the API pattern in lib/music_generator.py
    
    Args:
        prompt: MusicGen prompt string
        output_path: Path to save the generated audio file
        duration: Duration in seconds (max 30 for stereo-melody-large)
    
    Returns:
        True if successful, False otherwise
    """
    global current_prediction
    
    if not REPLICATE_AVAILABLE:
        print("[ERROR] Replicate not available")
        return False
    
    clean_prompt = prompt.strip().strip('"')
    
    prediction = None
    try:
        # Create prediction (same params as lib/music_generator.py)
        prediction = replicate.predictions.create(
            MUSICGEN_MODEL,
            input={
                "top_k": 250,
                "top_p": 0,
                "prompt": clean_prompt,
                "duration": min(duration, 30),
                "temperature": 1,
                "continuation": False,
                "model_version": "stereo-melody-large",
                "output_format": "wav",
                "continuation_start": 0,
                "multi_band_diffusion": False,
                "normalization_strategy": "loudness",
                "classifier_free_guidance": 3,
            },
        )
        
        current_prediction = prediction
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Generating music (ID: {prediction.id[:8]}...)...", total=None)
                prediction.wait()
        else:
            print(f"Generating music (ID: {prediction.id})...")
            prediction.wait()
        
        output = prediction.output
        current_prediction = None
        
        if output is None:
            print("[ERROR] Music generation failed. No output from API.")
            if prediction.logs:
                print("--- Replicate Logs ---")
                print(prediction.logs)
            return False
        
        # Handle different output formats (string, list, or bytes)
        audio_data = None
        
        if isinstance(output, str):
            # Single URL
            response = requests.get(output)
            response.raise_for_status()
            audio_data = response.content
        elif isinstance(output, list) and output and isinstance(output[0], str):
            # List with URL
            response = requests.get(output[0])
            response.raise_for_status()
            audio_data = response.content
        elif isinstance(output, bytes):
            # Raw bytes
            audio_data = output
        
        if not audio_data:
            print(f"[ERROR] Unexpected output format: {type(output)}")
            return False
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save audio file
        with open(output_path, 'wb') as f:
            f.write(audio_data)
        
        return True
        
    except KeyboardInterrupt:
        print("\n[CANCELLED] Cancelling generation...")
        if prediction:
            try:
                prediction.cancel()
            except Exception:
                pass
        return False
        
    except Exception as e:
        print(f"[ERROR] Generation failed: {e}")
        if prediction and prediction.logs:
            print("--- Replicate Logs ---")
            print(prediction.logs)
        return False


def cancel_current_prediction():
    """Cancel the currently running prediction if there is one."""
    global current_prediction
    if current_prediction:
        print("Cancelling current prediction...")
        try:
            current_prediction.cancel()
        except Exception as e:
            print(f"Error cancelling: {e}")
        current_prediction = None


# =============================================================================
# BATCH GENERATION
# =============================================================================

def generate_from_run(run_name: str, style: str = "default") -> Optional[Path]:
    """
    Generate music from a pipeline run's output.
    
    Args:
        run_name: Name of the run directory (e.g., "run_positive")
        style: Prompt style to use ("default", "minimal", "natural")
    
    Returns:
        Path to generated audio file, or None if failed
    """
    base_path = Path(__file__).parent / "outputs" / run_name
    
    # Load pipeline results
    results_file = base_path / "pipeline_results.json"
    if not results_file.exists():
        print(f"[ERROR] Results not found: {results_file}")
        return None
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    # Get the prompt
    prompt_data = results.get("prompt", {})
    
    if style == "minimal":
        prompt = prompt_data.get("prompt_minimal", "")
    elif style == "natural":
        prompt = prompt_data.get("prompt_natural", "")
    else:
        prompt = prompt_data.get("prompt", "")
    
    if not prompt:
        print(f"[ERROR] No prompt found in results")
        return None
    
    # Generate output path
    audio_dir = base_path / "audio"
    timestamp = datetime.now().strftime("%H%M%S")
    output_file = audio_dir / f"generated_{style}_{timestamp}.wav"
    
    # Show info
    if RICH_AVAILABLE:
        console.print(Panel(
            f"[bold]Run:[/bold] {run_name}\n"
            f"[bold]Style:[/bold] {style}\n"
            f"[bold]Prompt:[/bold] {prompt}",
            title="🎵 Generating Music",
            border_style="cyan"
        ))
    else:
        print(f"\n{'='*60}")
        print(f"Run: {run_name}")
        print(f"Style: {style}")
        print(f"Prompt: {prompt}")
        print('='*60)
    
    # Generate
    success = generate_music(prompt, str(output_file))
    
    if success:
        if RICH_AVAILABLE:
            console.print(f"[green]✓ Saved to:[/green] {output_file}")
        else:
            print(f"✓ Saved to: {output_file}")
        
        # Save metadata
        metadata_file = audio_dir / f"generated_{style}_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "run": run_name,
                "style": style,
                "prompt": prompt,
                "audio_file": output_file.name,
                "analysis": results.get("analysis", {}),
                "selection": {
                    "primary": results.get("selection", {}).get("primary"),
                    "secondary": results.get("selection", {}).get("secondary"),
                }
            }, f, indent=2)
        
        return output_file
    
    return None


def generate_all_runs(style: str = "default") -> dict:
    """Generate music for all completed runs."""
    outputs_dir = Path(__file__).parent / "outputs"
    
    runs = [d.name for d in outputs_dir.iterdir() 
            if d.is_dir() and d.name.startswith("run_")]
    
    if not runs:
        print("[ERROR] No runs found in outputs/")
        return {}
    
    if RICH_AVAILABLE:
        console.print(f"\n[bold]Found {len(runs)} runs to process[/bold]\n")
    else:
        print(f"\nFound {len(runs)} runs to process\n")
    
    results = {}
    for run in sorted(runs):
        output_file = generate_from_run(run, style)
        results[run] = output_file
        print()  # Spacing between runs
    
    # Summary
    if RICH_AVAILABLE:
        console.print("\n[bold]═══ Generation Summary ═══[/bold]")
        for run, path in results.items():
            if path:
                console.print(f"  [green]✓[/green] {run}: {path.name}")
            else:
                console.print(f"  [red]✗[/red] {run}: failed")
    else:
        print("\n=== Generation Summary ===")
        for run, path in results.items():
            status = f"✓ {path.name}" if path else "✗ failed"
            print(f"  {run}: {status}")
    
    return results


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate music from pipeline prompts using MusicGen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 04_generate_music.py --run run_positive
  python 04_generate_music.py --run run_negative --style minimal
  python 04_generate_music.py --all
  python 04_generate_music.py --prompt "ambient electronic, peaceful, 70 BPM"
        """
    )
    parser.add_argument("--run", "-r", type=str,
                       help="Run directory name (e.g., run_positive)")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Generate for all runs")
    parser.add_argument("--prompt", "-p", type=str,
                       help="Custom prompt to generate")
    parser.add_argument("--style", "-s", type=str,
                       choices=["default", "minimal", "natural"],
                       default="default",
                       help="Prompt style to use")
    parser.add_argument("--duration", "-d", type=int, default=30,
                       help="Duration in seconds (max 30)")
    parser.add_argument("--output", "-o", type=str,
                       help="Output file path (for custom prompt)")
    
    args = parser.parse_args()
    
    if not REPLICATE_AVAILABLE:
        print("[ERROR] Replicate library not available")
        sys.exit(1)
    
    if args.prompt:
        # Generate from custom prompt
        if args.output:
            output_file = args.output
        else:
            output_dir = Path(__file__).parent / "outputs" / "custom"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(output_dir / f"custom_{timestamp}.wav")
        
        if RICH_AVAILABLE:
            console.print(Panel(f"[bold]Prompt:[/bold] {args.prompt}", title="Custom Generation"))
        else:
            print(f"Prompt: {args.prompt}")
        
        success = generate_music(args.prompt, output_file, args.duration)
        
        if success:
            print(f"✓ Saved to: {output_file}")
        else:
            sys.exit(1)
    
    elif args.all:
        # Generate for all runs
        generate_all_runs(args.style)
    
    elif args.run:
        # Generate for specific run
        result = generate_from_run(args.run, args.style)
        if not result:
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
