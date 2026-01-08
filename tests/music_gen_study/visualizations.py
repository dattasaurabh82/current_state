"""
SVG Visualizations Module

Generates beautiful SVG visualizations for the music generation pipeline:
1. Mood Radar - 4-axis chart showing analysis dimensions
2. Archetype Wheel - Shows all archetypes with scores
3. Prompt DNA - Visual breakdown of prompt components

Usage:
    from visualizations import generate_mood_radar, generate_archetype_wheel, generate_prompt_dna
    
    svg = generate_mood_radar(valence=0.3, tension=0.6, hope=0.5, energy="medium")
    save_svg(svg, "outputs/visualizations/mood_radar.svg")
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import date


# =============================================================================
# COLOR PALETTES
# =============================================================================

COLORS = {
    # Main palette (soft, sophisticated)
    "primary": "#6366f1",      # Indigo
    "secondary": "#8b5cf6",    # Violet
    "accent": "#ec4899",       # Pink
    "positive": "#10b981",     # Emerald
    "negative": "#ef4444",     # Red
    "neutral": "#6b7280",      # Gray
    
    # Background/structure
    "bg": "#1e1e2e",           # Dark blue-gray
    "bg_light": "#2d2d3d",     # Lighter
    "grid": "#3d3d4d",         # Grid lines
    "text": "#e2e8f0",         # Light text
    "text_dim": "#94a3b8",     # Dimmed text
    
    # Archetype colors
    "tranquil_optimism": "#34d399",
    "reflective_calm": "#60a5fa",
    "gentle_tension": "#fbbf24",
    "melancholic_beauty": "#a78bfa",
    "cautious_hope": "#2dd4bf",
    "serene_resilience": "#f472b6",
}


# =============================================================================
# SVG HELPERS
# =============================================================================

def svg_header(width: int, height: int, title: str = "") -> str:
    """Generate SVG header with embedded styles."""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <title>{title}</title>
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;display=swap');
      .title {{ font-family: 'Inter', sans-serif; font-size: 18px; font-weight: 600; fill: {COLORS["text"]}; }}
      .label {{ font-family: 'Inter', sans-serif; font-size: 12px; font-weight: 500; fill: {COLORS["text"]}; }}
      .value {{ font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 600; fill: {COLORS["text"]}; }}
      .dim {{ fill: {COLORS["text_dim"]}; }}
      .small {{ font-size: 10px; }}
    </style>
    <linearGradient id="primaryGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['secondary']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="100%" height="100%" fill="{COLORS['bg']}"/>
'''


def svg_footer() -> str:
    return "</svg>"


def polar_to_cartesian(cx: float, cy: float, radius: float, angle_deg: float) -> Tuple[float, float]:
    """Convert polar coordinates to cartesian."""
    angle_rad = math.radians(angle_deg - 90)  # Start from top
    x = cx + radius * math.cos(angle_rad)
    y = cy + radius * math.sin(angle_rad)
    return x, y


# =============================================================================
# MOOD RADAR VISUALIZATION
# =============================================================================

def generate_mood_radar(
    valence: float,          # -1 to +1
    tension: float,          # 0 to 1
    hope: float,             # 0 to 1
    energy: str,             # "low", "medium", "high"
    date_str: str = None,
) -> str:
    """
    Generate a 4-axis radar chart showing mood dimensions.
    
    Axes:
    - Top: Hope (0-1)
    - Right: Tension (0-1)  
    - Bottom: Valence (-1 to +1, normalized)
    - Left: Energy (low=0.33, medium=0.66, high=1.0)
    """
    width, height = 400, 450
    cx, cy = 200, 200
    max_radius = 120
    
    # Normalize values
    hope_norm = hope
    tension_norm = tension
    valence_norm = (valence + 1) / 2  # Convert -1..+1 to 0..1
    energy_map = {"low": 0.33, "medium": 0.66, "high": 1.0}
    energy_norm = energy_map.get(energy.lower(), 0.5)
    
    # Axis angles (clockwise from top)
    angles = [0, 90, 180, 270]  # Hope, Tension, Valence, Energy
    values = [hope_norm, tension_norm, valence_norm, energy_norm]
    labels = ["Hope", "Tension", "Valence", "Energy"]
    
    svg = svg_header(width, height, "Mood Radar")
    
    # Title
    title_text = "Mood Analysis"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{cx}" y="35" text-anchor="middle" class="title">{title_text}</text>\n'
    
    # Draw grid circles
    for i, r in enumerate([0.25, 0.5, 0.75, 1.0]):
        radius = r * max_radius
        opacity = 0.3 if r < 1.0 else 0.6
        svg += f'  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{COLORS["grid"]}" stroke-opacity="{opacity}" stroke-width="1"/>\n'
    
    # Draw axis lines
    for angle in angles:
        x, y = polar_to_cartesian(cx, cy, max_radius + 10, angle)
        svg += f'  <line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="{COLORS["grid"]}" stroke-width="1" stroke-opacity="0.5"/>\n'
    
    # Draw axis labels
    label_offsets = [(0, -20), (25, 0), (0, 25), (-25, 0)]
    for i, (angle, label) in enumerate(zip(angles, labels)):
        x, y = polar_to_cartesian(cx, cy, max_radius + 30, angle)
        ox, oy = label_offsets[i]
        svg += f'  <text x="{x + ox}" y="{y + oy}" text-anchor="middle" class="label">{label}</text>\n'
    
    # Draw data polygon
    points = []
    for angle, value in zip(angles, values):
        radius = value * max_radius
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        points.append(f"{x:.1f},{y:.1f}")
    
    svg += f'  <polygon points="{" ".join(points)}" fill="url(#primaryGradient)" fill-opacity="0.3" stroke="{COLORS["primary"]}" stroke-width="2" filter="url(#glow)"/>\n'
    
    # Draw data points
    for i, (angle, value) in enumerate(zip(angles, values)):
        radius = value * max_radius
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        svg += f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{COLORS["primary"]}" stroke="{COLORS["bg"]}" stroke-width="2"/>\n'
    
    # Value labels (inside the chart)
    value_labels = [
        f"{hope:.2f}",
        f"{tension:.2f}",
        f"{valence:+.2f}",
        energy.upper()
    ]
    
    for i, (angle, val_label, value) in enumerate(zip(angles, value_labels, values)):
        radius = max(value * max_radius - 25, 20)
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        svg += f'  <text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" class="value small">{val_label}</text>\n'
    
    # Legend / summary at bottom
    summary_y = 380
    svg += f'  <text x="{cx}" y="{summary_y}" text-anchor="middle" class="label dim">Overall: '
    
    if valence > 0.3:
        mood = "Optimistic"
    elif valence < -0.3:
        mood = "Somber"
    else:
        mood = "Balanced"
    
    if tension > 0.6:
        mood += ", Tense"
    elif tension < 0.3:
        mood += ", Calm"
    
    svg += f'{mood}</text>\n'
    
    svg += svg_footer()
    return svg


# =============================================================================
# ARCHETYPE WHEEL VISUALIZATION
# =============================================================================

def generate_archetype_wheel(
    scores: Dict[str, float],
    primary: str,
    secondary: str = None,
    date_str: str = None,
) -> str:
    """
    Generate a wheel visualization showing all archetype scores.
    """
    width, height = 450, 500
    cx, cy = 225, 230
    inner_radius = 50
    max_radius = 140
    
    archetypes = [
        "tranquil_optimism",
        "serene_resilience",
        "cautious_hope",
        "gentle_tension",
        "melancholic_beauty",
        "reflective_calm",
    ]
    
    svg = svg_header(width, height, "Archetype Selection")
    
    # Title
    title_text = "Archetype Scores"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{cx}" y="35" text-anchor="middle" class="title">{title_text}</text>\n'
    
    # Draw segments
    n = len(archetypes)
    angle_per_segment = 360 / n
    
    for i, archetype in enumerate(archetypes):
        score = scores.get(archetype, 0)
        start_angle = i * angle_per_segment
        end_angle = start_angle + angle_per_segment
        
        # Calculate arc
        radius = inner_radius + (max_radius - inner_radius) * score
        
        # Determine colors
        if archetype == primary:
            fill_color = COLORS.get(archetype, COLORS["primary"])
            stroke_color = COLORS["text"]
            stroke_width = 3
            opacity = 0.9
        elif archetype == secondary:
            fill_color = COLORS.get(archetype, COLORS["secondary"])
            stroke_color = COLORS["text"]
            stroke_width = 2
            opacity = 0.7
        else:
            fill_color = COLORS.get(archetype, COLORS["neutral"])
            stroke_color = COLORS["grid"]
            stroke_width = 1
            opacity = 0.4
        
        # Create arc path
        x1_inner, y1_inner = polar_to_cartesian(cx, cy, inner_radius, start_angle)
        x2_inner, y2_inner = polar_to_cartesian(cx, cy, inner_radius, end_angle)
        x1_outer, y1_outer = polar_to_cartesian(cx, cy, radius, start_angle)
        x2_outer, y2_outer = polar_to_cartesian(cx, cy, radius, end_angle)
        
        large_arc = 0  # segments are < 180 degrees
        
        path = f"M {x1_inner:.1f} {y1_inner:.1f} "
        path += f"L {x1_outer:.1f} {y1_outer:.1f} "
        path += f"A {radius:.1f} {radius:.1f} 0 {large_arc} 1 {x2_outer:.1f} {y2_outer:.1f} "
        path += f"L {x2_inner:.1f} {y2_inner:.1f} "
        path += f"A {inner_radius:.1f} {inner_radius:.1f} 0 {large_arc} 0 {x1_inner:.1f} {y1_inner:.1f} Z"
        
        svg += f'  <path d="{path}" fill="{fill_color}" fill-opacity="{opacity}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>\n'
        
        # Label
        mid_angle = (start_angle + end_angle) / 2
        label_radius = max_radius + 30
        lx, ly = polar_to_cartesian(cx, cy, label_radius, mid_angle)
        
        # Format label
        label = archetype.replace("_", " ").title()
        short_label = label.split()[0]  # Just first word for compactness
        
        # Anchor based on position
        if mid_angle < 180:
            anchor = "start" if mid_angle < 90 or mid_angle > 90 else "middle"
        else:
            anchor = "end" if mid_angle > 270 or mid_angle < 270 else "middle"
        
        if 45 < mid_angle < 135:
            anchor = "start"
        elif 135 < mid_angle < 225:
            anchor = "middle"
        elif 225 < mid_angle < 315:
            anchor = "end"
        else:
            anchor = "middle"
        
        svg += f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" class="label small">{short_label}</text>\n'
        
        # Score value
        score_radius = inner_radius + (max_radius - inner_radius) * score / 2 + 10
        sx, sy = polar_to_cartesian(cx, cy, score_radius, mid_angle)
        svg += f'  <text x="{sx:.1f}" y="{sy:.1f}" text-anchor="middle" dominant-baseline="middle" class="value small">{score:.2f}</text>\n'
    
    # Center label
    svg += f'  <circle cx="{cx}" cy="{cy}" r="{inner_radius - 5}" fill="{COLORS["bg_light"]}"/>\n'
    
    primary_short = primary.replace("_", " ").split()[0].title() if primary else "?"
    svg += f'  <text x="{cx}" y="{cy - 5}" text-anchor="middle" class="label">Primary</text>\n'
    svg += f'  <text x="{cx}" y="{cy + 15}" text-anchor="middle" class="value">{primary_short}</text>\n'
    
    # Legend at bottom
    legend_y = 430
    svg += f'  <rect x="50" y="{legend_y}" width="15" height="15" fill="{COLORS.get(primary, COLORS["primary"])}" fill-opacity="0.9" rx="3"/>\n'
    svg += f'  <text x="75" y="{legend_y + 12}" class="label small">Primary</text>\n'
    
    if secondary:
        svg += f'  <rect x="150" y="{legend_y}" width="15" height="15" fill="{COLORS.get(secondary, COLORS["secondary"])}" fill-opacity="0.7" rx="3"/>\n'
        svg += f'  <text x="175" y="{legend_y + 12}" class="label small">Secondary</text>\n'
    
    svg += svg_footer()
    return svg


# =============================================================================
# PROMPT DNA VISUALIZATION
# =============================================================================

def generate_prompt_dna(
    genre: str,
    instruments: List[str],
    moods: List[str],
    themes: List[str],
    tempo: int,
    intensity: str,
    primary_archetype: str,
    date_str: str = None,
) -> str:
    """
    Generate a visual breakdown of prompt components.
    Shows the "DNA" of what went into the final prompt.
    """
    width, height = 500, 400
    
    svg = svg_header(width, height, "Prompt DNA")
    
    # Title
    title_text = "Prompt Composition"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{width/2}" y="30" text-anchor="middle" class="title">{title_text}</text>\n'
    
    # Three columns: Structure | Color | Output
    col_width = 150
    col_starts = [30, 180, 330]
    
    # Column headers
    headers = ["STRUCTURE", "COLOR", "OUTPUT"]
    header_colors = [COLORS["positive"], COLORS["accent"], COLORS["primary"]]
    
    for i, (header, col_x, color) in enumerate(zip(headers, col_starts, header_colors)):
        svg += f'  <text x="{col_x + col_width/2}" y="60" text-anchor="middle" class="label" fill="{color}">{header}</text>\n'
        svg += f'  <line x1="{col_x}" y1="70" x2="{col_x + col_width - 10}" y2="70" stroke="{color}" stroke-width="2" stroke-opacity="0.5"/>\n'
    
    # Structure column
    y = 95
    svg += f'  <text x="{col_starts[0]}" y="{y}" class="label dim">Archetype</text>\n'
    svg += f'  <text x="{col_starts[0]}" y="{y + 18}" class="value">{primary_archetype.replace("_", " ").title()}</text>\n'
    
    y += 50
    svg += f'  <text x="{col_starts[0]}" y="{y}" class="label dim">Genre</text>\n'
    svg += f'  <text x="{col_starts[0]}" y="{y + 18}" class="value">{genre}</text>\n'
    
    y += 50
    svg += f'  <text x="{col_starts[0]}" y="{y}" class="label dim">Tempo</text>\n'
    svg += f'  <text x="{col_starts[0]}" y="{y + 18}" class="value">{tempo} BPM</text>\n'
    
    y += 50
    svg += f'  <text x="{col_starts[0]}" y="{y}" class="label dim">Intensity</text>\n'
    svg += f'  <text x="{col_starts[0]}" y="{y + 18}" class="value">{intensity.upper()}</text>\n'
    
    # Color column
    y = 95
    svg += f'  <text x="{col_starts[1]}" y="{y}" class="label dim">Themes</text>\n'
    for i, theme in enumerate(themes[:3]):
        svg += f'  <text x="{col_starts[1]}" y="{y + 18 + i*16}" class="value small">{theme}</text>\n'
    
    y += 80
    svg += f'  <text x="{col_starts[1]}" y="{y}" class="label dim">Moods</text>\n'
    for i, mood in enumerate(moods[:3]):
        svg += f'  <text x="{col_starts[1]}" y="{y + 18 + i*16}" class="value small">{mood}</text>\n'
    
    # Output column
    y = 95
    svg += f'  <text x="{col_starts[2]}" y="{y}" class="label dim">Instruments</text>\n'
    for i, inst in enumerate(instruments[:3]):
        # Truncate long instrument names
        inst_short = inst[:20] + "..." if len(inst) > 20 else inst
        svg += f'  <text x="{col_starts[2]}" y="{y + 18 + i*18}" class="value small">{inst_short}</text>\n'
    
    y += 90
    svg += f'  <text x="{col_starts[2]}" y="{y}" class="label dim">Characteristics</text>\n'
    characteristics = moods[:2] + [f"{tempo} BPM"]
    for i, char in enumerate(characteristics):
        svg += f'  <text x="{col_starts[2]}" y="{y + 18 + i*16}" class="value small">{char}</text>\n'
    
    # Flow arrows
    arrow_y = 180
    svg += f'  <line x1="{col_starts[0] + col_width - 20}" y1="{arrow_y}" x2="{col_starts[1] - 10}" y2="{arrow_y}" stroke="{COLORS["grid"]}" stroke-width="2" marker-end="url(#arrowhead)"/>\n'
    svg += f'  <line x1="{col_starts[1] + col_width - 20}" y1="{arrow_y}" x2="{col_starts[2] - 10}" y2="{arrow_y}" stroke="{COLORS["grid"]}" stroke-width="2" marker-end="url(#arrowhead)"/>\n'
    
    # Add arrowhead marker
    svg = svg.replace("</defs>", '''
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#3d3d4d" />
    </marker>
  </defs>''')
    
    # Bottom: final prompt preview
    svg += f'  <rect x="30" y="320" width="{width - 60}" height="60" fill="{COLORS["bg_light"]}" rx="8"/>\n'
    svg += f'  <text x="50" y="345" class="label dim">Generated Prompt</text>\n'
    
    # Truncated prompt preview
    prompt_preview = f"{genre}, {instruments[0] if instruments else ''}, {moods[0] if moods else ''}, {tempo} BPM"
    if len(prompt_preview) > 60:
        prompt_preview = prompt_preview[:57] + "..."
    svg += f'  <text x="50" y="365" class="value small">{prompt_preview}</text>\n'
    
    svg += svg_footer()
    return svg


# =============================================================================
# FILE I/O
# =============================================================================

def save_svg(svg_content: str, filepath: str):
    """Save SVG content to file."""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(svg_content)


def generate_all_visualizations(
    analysis: dict,
    selection: dict,
    prompt_components: dict,
    output_dir: str,
    date_str: str = None,
):
    """Generate all visualizations and save to directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if date_str is None:
        date_str = date.today().isoformat()
    
    # 1. Mood Radar
    mood_svg = generate_mood_radar(
        valence=analysis.get("emotional_valence", 0),
        tension=analysis.get("tension_level", 0.5),
        hope=analysis.get("hope_factor", 0.5),
        energy=analysis.get("energy_level", "medium"),
        date_str=date_str,
    )
    save_svg(mood_svg, output_path / "mood_radar.svg")
    
    # 2. Archetype Wheel
    scores = {s["archetype"]: s["score"] for s in selection.get("all_scores", [])}
    wheel_svg = generate_archetype_wheel(
        scores=scores,
        primary=selection.get("primary", ""),
        secondary=selection.get("secondary"),
        date_str=date_str,
    )
    save_svg(wheel_svg, output_path / "archetype_wheel.svg")
    
    # 3. Prompt DNA
    dna_svg = generate_prompt_dna(
        genre=prompt_components.get("genre", "ambient"),
        instruments=prompt_components.get("base_instruments", []),
        moods=prompt_components.get("base_moods", []),
        themes=prompt_components.get("source_themes", []),
        tempo=prompt_components.get("tempo_final", 70),
        intensity=prompt_components.get("intensity_level", "medium"),
        primary_archetype=prompt_components.get("primary_archetype", ""),
        date_str=date_str,
    )
    save_svg(dna_svg, output_path / "prompt_dna.svg")
    
    return [
        str(output_path / "mood_radar.svg"),
        str(output_path / "archetype_wheel.svg"),
        str(output_path / "prompt_dna.svg"),
    ]


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("Generating test visualizations...")
    
    # Test data
    test_analysis = {
        "emotional_valence": 0.1,
        "tension_level": 0.6,
        "hope_factor": 0.5,
        "energy_level": "medium",
    }
    
    test_selection = {
        "primary": "cautious_hope",
        "secondary": "gentle_tension",
        "all_scores": [
            {"archetype": "cautious_hope", "score": 0.92},
            {"archetype": "gentle_tension", "score": 0.90},
            {"archetype": "reflective_calm", "score": 0.77},
            {"archetype": "serene_resilience", "score": 0.74},
            {"archetype": "melancholic_beauty", "score": 0.63},
            {"archetype": "tranquil_optimism", "score": 0.37},
        ]
    }
    
    test_components = {
        "genre": "ambient electronic",
        "base_instruments": ["soft synths", "gentle bells", "atmospheric pads"],
        "base_moods": ["hopeful", "restrained", "thoughtful"],
        "source_themes": ["politics", "economy", "technology"],
        "tempo_final": 71,
        "intensity_level": "high",
        "primary_archetype": "cautious_hope",
    }
    
    output_dir = Path(__file__).parent / "outputs" / "visualizations"
    
    files = generate_all_visualizations(
        analysis=test_analysis,
        selection=test_selection,
        prompt_components=test_components,
        output_dir=str(output_dir),
        date_str="2026-01-08",
    )
    
    print(f"\nGenerated {len(files)} visualizations:")
    for f in files:
        print(f"  - {f}")
