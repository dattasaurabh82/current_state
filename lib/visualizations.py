"""
SVG Visualizations Module

Generates SVG visualizations for the music generation pipeline:
1. Mood Radar - 4-axis chart showing analysis dimensions
2. Archetype Wheel - Shows all archetypes with scores
3. Prompt DNA - Visual breakdown of prompt components
"""

import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import date


# =============================================================================
# COLOR PALETTES
# =============================================================================

COLORS = {
    "primary": "#6366f1",
    "secondary": "#8b5cf6",
    "accent": "#ec4899",
    "positive": "#10b981",
    "negative": "#ef4444",
    "neutral": "#6b7280",
    "bg": "#1e1e2e",
    "bg_light": "#2d2d3d",
    "grid": "#3d3d4d",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
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
    angle_rad = math.radians(angle_deg - 90)
    x = cx + radius * math.cos(angle_rad)
    y = cy + radius * math.sin(angle_rad)
    return x, y


# =============================================================================
# MOOD RADAR VISUALIZATION
# =============================================================================

def generate_mood_radar(
    valence: float,
    tension: float,
    hope: float,
    energy: str,
    date_str: str = None,
) -> str:
    width, height = 400, 450
    cx, cy = 200, 200
    max_radius = 120
    
    hope_norm = hope
    tension_norm = tension
    valence_norm = (valence + 1) / 2
    energy_map = {"low": 0.33, "medium": 0.66, "high": 1.0}
    energy_norm = energy_map.get(energy.lower(), 0.5)
    
    angles = [0, 90, 180, 270]
    values = [hope_norm, tension_norm, valence_norm, energy_norm]
    labels = ["Hope", "Tension", "Valence", "Energy"]
    
    svg = svg_header(width, height, "Mood Radar")
    
    title_text = "Mood Analysis"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{cx}" y="35" text-anchor="middle" class="title">{title_text}</text>\n'
    
    for i, r in enumerate([0.25, 0.5, 0.75, 1.0]):
        radius = r * max_radius
        opacity = 0.3 if r < 1.0 else 0.6
        svg += f'  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{COLORS["grid"]}" stroke-opacity="{opacity}" stroke-width="1"/>\n'
    
    for angle in angles:
        x, y = polar_to_cartesian(cx, cy, max_radius + 10, angle)
        svg += f'  <line x1="{cx}" y1="{cy}" x2="{x}" y2="{y}" stroke="{COLORS["grid"]}" stroke-width="1" stroke-opacity="0.5"/>\n'
    
    label_offsets = [(0, -20), (25, 0), (0, 25), (-25, 0)]
    for i, (angle, label) in enumerate(zip(angles, labels)):
        x, y = polar_to_cartesian(cx, cy, max_radius + 30, angle)
        ox, oy = label_offsets[i]
        svg += f'  <text x="{x + ox}" y="{y + oy}" text-anchor="middle" class="label">{label}</text>\n'
    
    points = []
    for angle, value in zip(angles, values):
        radius = value * max_radius
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        points.append(f"{x:.1f},{y:.1f}")
    
    svg += f'  <polygon points="{" ".join(points)}" fill="url(#primaryGradient)" fill-opacity="0.3" stroke="{COLORS["primary"]}" stroke-width="2" filter="url(#glow)"/>\n'
    
    for i, (angle, value) in enumerate(zip(angles, values)):
        radius = value * max_radius
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        svg += f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{COLORS["primary"]}" stroke="{COLORS["bg"]}" stroke-width="2"/>\n'
    
    value_labels = [f"{hope:.2f}", f"{tension:.2f}", f"{valence:+.2f}", energy.upper()]
    
    for i, (angle, val_label, value) in enumerate(zip(angles, value_labels, values)):
        radius = max(value * max_radius - 25, 20)
        x, y = polar_to_cartesian(cx, cy, radius, angle)
        svg += f'  <text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="middle" class="value small">{val_label}</text>\n'
    
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
    width, height = 450, 500
    cx, cy = 225, 230
    inner_radius = 50
    max_radius = 140
    
    archetypes = [
        "tranquil_optimism", "serene_resilience", "cautious_hope",
        "gentle_tension", "melancholic_beauty", "reflective_calm",
    ]
    
    svg = svg_header(width, height, "Archetype Selection")
    
    title_text = "Archetype Scores"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{cx}" y="35" text-anchor="middle" class="title">{title_text}</text>\n'
    
    n = len(archetypes)
    angle_per_segment = 360 / n
    
    for i, archetype in enumerate(archetypes):
        score = scores.get(archetype, 0)
        start_angle = i * angle_per_segment
        end_angle = start_angle + angle_per_segment
        
        radius = inner_radius + (max_radius - inner_radius) * score
        
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
        
        x1_inner, y1_inner = polar_to_cartesian(cx, cy, inner_radius, start_angle)
        x2_inner, y2_inner = polar_to_cartesian(cx, cy, inner_radius, end_angle)
        x1_outer, y1_outer = polar_to_cartesian(cx, cy, radius, start_angle)
        x2_outer, y2_outer = polar_to_cartesian(cx, cy, radius, end_angle)
        
        large_arc = 0
        
        path = f"M {x1_inner:.1f} {y1_inner:.1f} "
        path += f"L {x1_outer:.1f} {y1_outer:.1f} "
        path += f"A {radius:.1f} {radius:.1f} 0 {large_arc} 1 {x2_outer:.1f} {y2_outer:.1f} "
        path += f"L {x2_inner:.1f} {y2_inner:.1f} "
        path += f"A {inner_radius:.1f} {inner_radius:.1f} 0 {large_arc} 0 {x1_inner:.1f} {y1_inner:.1f} Z"
        
        svg += f'  <path d="{path}" fill="{fill_color}" fill-opacity="{opacity}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>\n'
        
        mid_angle = (start_angle + end_angle) / 2
        label_radius = max_radius + 30
        lx, ly = polar_to_cartesian(cx, cy, label_radius, mid_angle)
        
        label = archetype.replace("_", " ").title()
        short_label = label.split()[0]
        
        if 45 < mid_angle < 135:
            anchor = "start"
        elif 135 < mid_angle < 225:
            anchor = "middle"
        elif 225 < mid_angle < 315:
            anchor = "end"
        else:
            anchor = "middle"
        
        svg += f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" class="label small">{short_label}</text>\n'
        
        score_radius = inner_radius + (max_radius - inner_radius) * score / 2 + 10
        sx, sy = polar_to_cartesian(cx, cy, score_radius, mid_angle)
        svg += f'  <text x="{sx:.1f}" y="{sy:.1f}" text-anchor="middle" dominant-baseline="middle" class="value small">{score:.2f}</text>\n'
    
    svg += f'  <circle cx="{cx}" cy="{cy}" r="{inner_radius - 5}" fill="{COLORS["bg_light"]}"/>\n'
    
    primary_short = primary.replace("_", " ").split()[0].title() if primary else "?"
    svg += f'  <text x="{cx}" y="{cy - 5}" text-anchor="middle" class="label">Primary</text>\n'
    svg += f'  <text x="{cx}" y="{cy + 15}" text-anchor="middle" class="value">{primary_short}</text>\n'
    
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
    width, height = 500, 400
    
    svg = svg_header(width, height, "Prompt DNA")
    
    title_text = "Prompt Composition"
    if date_str:
        title_text += f" — {date_str}"
    svg += f'  <text x="{width/2}" y="30" text-anchor="middle" class="title">{title_text}</text>\n'
    
    col_width = 150
    col_starts = [30, 180, 330]
    
    headers = ["STRUCTURE", "COLOR", "OUTPUT"]
    header_colors = [COLORS["positive"], COLORS["accent"], COLORS["primary"]]
    
    for i, (header, col_x, color) in enumerate(zip(headers, col_starts, header_colors)):
        svg += f'  <text x="{col_x + col_width/2}" y="60" text-anchor="middle" class="label" fill="{color}">{header}</text>\n'
        svg += f'  <line x1="{col_x}" y1="70" x2="{col_x + col_width - 10}" y2="70" stroke="{color}" stroke-width="2" stroke-opacity="0.5"/>\n'
    
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
    
    y = 95
    svg += f'  <text x="{col_starts[1]}" y="{y}" class="label dim">Themes</text>\n'
    for i, theme in enumerate(themes[:3]):
        svg += f'  <text x="{col_starts[1]}" y="{y + 18 + i*16}" class="value small">{theme}</text>\n'
    
    y += 80
    svg += f'  <text x="{col_starts[1]}" y="{y}" class="label dim">Moods</text>\n'
    for i, mood in enumerate(moods[:3]):
        svg += f'  <text x="{col_starts[1]}" y="{y + 18 + i*16}" class="value small">{mood}</text>\n'
    
    y = 95
    svg += f'  <text x="{col_starts[2]}" y="{y}" class="label dim">Instruments</text>\n'
    for i, inst in enumerate(instruments[:3]):
        inst_short = inst[:20] + "..." if len(inst) > 20 else inst
        svg += f'  <text x="{col_starts[2]}" y="{y + 18 + i*18}" class="value small">{inst_short}</text>\n'
    
    y += 90
    svg += f'  <text x="{col_starts[2]}" y="{y}" class="label dim">Characteristics</text>\n'
    characteristics = moods[:2] + [f"{tempo} BPM"]
    for i, char in enumerate(characteristics):
        svg += f'  <text x="{col_starts[2]}" y="{y + 18 + i*16}" class="value small">{char}</text>\n'
    
    arrow_y = 180
    svg += f'  <line x1="{col_starts[0] + col_width - 20}" y1="{arrow_y}" x2="{col_starts[1] - 10}" y2="{arrow_y}" stroke="{COLORS["grid"]}" stroke-width="2" marker-end="url(#arrowhead)"/>\n'
    svg += f'  <line x1="{col_starts[1] + col_width - 20}" y1="{arrow_y}" x2="{col_starts[2] - 10}" y2="{arrow_y}" stroke="{COLORS["grid"]}" stroke-width="2" marker-end="url(#arrowhead)"/>\n'
    
    svg = svg.replace("</defs>", '''
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#3d3d4d" />
    </marker>
  </defs>''')
    
    svg += f'  <rect x="30" y="320" width="{width - 60}" height="60" fill="{COLORS["bg_light"]}" rx="8"/>\n'
    svg += f'  <text x="50" y="345" class="label dim">Generated Prompt</text>\n'
    
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
) -> List[str]:
    """Generate all visualizations and save to directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if date_str is None:
        date_str = date.today().isoformat()
    
    mood_svg = generate_mood_radar(
        valence=analysis.get("emotional_valence", 0),
        tension=analysis.get("tension_level", 0.5),
        hope=analysis.get("hope_factor", 0.5),
        energy=analysis.get("energy_level", "medium"),
        date_str=date_str,
    )
    save_svg(mood_svg, output_path / "mood_radar.svg")
    
    scores = {s["archetype"]: s["score"] for s in selection.get("all_scores", [])}
    wheel_svg = generate_archetype_wheel(
        scores=scores,
        primary=selection.get("primary", ""),
        secondary=selection.get("secondary"),
        date_str=date_str,
    )
    save_svg(wheel_svg, output_path / "archetype_wheel.svg")
    
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
