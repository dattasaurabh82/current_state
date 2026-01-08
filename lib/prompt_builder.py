"""
Prompt Builder Module

Combines three layers for varied, nuanced MusicGen prompts:
1. STRUCTURE (Archetype) - Base genre, core instruments, tempo range
2. COLOR (Theme Textures) - Timbral, movement, harmonic character
3. VARIETY (Daily Seed) - Controlled randomness for day-to-day freshness
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import date
import random
from loguru import logger

from lib.archetypes import (
    ArchetypeName,
    get_archetype,
)

from lib.theme_textures import (
    blend_textures,
    DailyVariation,
)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PromptComponents:
    """Full breakdown of prompt components."""
    genre: str
    base_instruments: List[str]
    base_moods: List[str]
    base_tempo: int
    texture_timbre: List[str]
    texture_movement: List[str]
    texture_harmonic: List[str]
    tempo_final: int
    instrument_variant: int
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
    "low": {"adjectives": ["soft", "gentle", "subtle", "delicate", "light"], "tempo_adjust": -3},
    "medium": {"adjectives": ["warm", "flowing", "smooth", "balanced"], "tempo_adjust": 0},
    "high": {"adjectives": ["deep", "rich", "layered", "evolving", "expansive"], "tempo_adjust": +3},
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
    """Build a nuanced MusicGen prompt combining structure, color, and variety."""
    if date_seed is None:
        date_seed = date.today()
    if themes is None:
        themes = []
    
    primary_desc = get_archetype(primary)
    secondary_desc = get_archetype(secondary) if secondary else None
    daily_var = DailyVariation.from_date(date_seed)
    texture_blend = blend_textures(themes, date_seed=date_seed) if themes else None
    intensity = INTENSITY_CONFIG.get(intensity_level, INTENSITY_CONFIG["medium"])
    
    # LAYER 1: STRUCTURE
    genre = primary_desc.genre
    
    instruments = list(primary_desc.instruments[:2])
    if secondary_desc:
        for inst in secondary_desc.instruments:
            if inst not in instruments:
                instruments.append(inst)
                break
    
    if len(instruments) > 1 and daily_var.instrument_rotation > 0:
        rotation = daily_var.instrument_rotation % len(instruments)
        instruments = instruments[rotation:] + instruments[:rotation]
    
    moods = list(primary_desc.mood_musical[:1] + primary_desc.mood_emotional[:1])
    if secondary_desc:
        for mood in secondary_desc.mood_emotional:
            if mood not in moods:
                moods.append(mood)
                break
    
    rng = random.Random(daily_var.mood_shuffle_seed)
    rng.shuffle(moods)
    
    base_tempo = primary_desc.tempo_value
    if secondary_desc and blend_ratio:
        base_tempo = int(base_tempo * blend_ratio + secondary_desc.tempo_value * (1 - blend_ratio))
    
    tempo_adjusted = base_tempo + intensity["tempo_adjust"]
    tempo_final = tempo_adjusted + daily_var.tempo_nudge
    
    # LAYER 2: COLOR
    texture_timbre, texture_movement, texture_harmonic, source_themes = [], [], [], []
    
    if texture_blend:
        texture_timbre = texture_blend.timbre_words
        texture_movement = texture_blend.movement_words
        texture_harmonic = texture_blend.harmonic_words
        source_themes = texture_blend.source_themes
        
        if daily_var.texture_emphasis == "movement" and texture_movement:
            if texture_movement[0] not in moods:
                moods.append(texture_movement[0])
        elif daily_var.texture_emphasis == "harmonic" and texture_harmonic:
            if texture_harmonic[0] not in moods:
                moods.append(texture_harmonic[0])
    
    # LAYER 3: VARIETY
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
    
    if len(instruments) > 1 and texture_timbre:
        second_inst = instruments[1]
        has_adjective = any(
            second_inst.lower().startswith(adj) 
            for adj in texture_timbre + ["soft", "gentle", "warm", "deep"]
        )
        if not has_adjective:
            instruments[1] = f"{texture_timbre[0]} {second_inst}"
    
    components = PromptComponents(
        genre=genre,
        base_instruments=instruments,
        base_moods=moods[:4],
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
    
    prompt_default = _assemble_prompt_default(components)
    prompt_minimal = _assemble_prompt_minimal(components)
    prompt_natural = _assemble_prompt_natural(components)
    
    logger.info(f"[Builder] Genre: {genre}, Tempo: {tempo_final} BPM")
    logger.debug(f"[Builder] Instruments: {instruments}")
    logger.debug(f"[Builder] Moods: {moods[:4]}")
    
    return PromptResult(
        prompt=prompt_default,
        prompt_minimal=prompt_minimal,
        prompt_natural=prompt_natural,
        components=components,
    )


# =============================================================================
# PROMPT ASSEMBLY FUNCTIONS
# =============================================================================

def _get_tempo_descriptor(bpm: int) -> str:
    if bpm < 55:
        return "very slow"
    elif bpm < 65:
        return "slow"
    elif bpm < 75:
        return "moderate"
    elif bpm < 90:
        return "medium"
    return "flowing"


def _assemble_prompt_default(c: PromptComponents) -> str:
    """Default prompt style - balanced and descriptive."""
    parts = [c.genre.capitalize()]
    
    if c.base_instruments:
        if len(c.base_instruments) == 1:
            inst_str = c.base_instruments[0]
        elif len(c.base_instruments) == 2:
            inst_str = f"{c.base_instruments[0]} and {c.base_instruments[1]}"
        else:
            inst_str = ", ".join(c.base_instruments[:-1]) + f" and {c.base_instruments[-1]}"
        parts.append(f"with {inst_str}")
    
    if c.base_moods:
        unique_moods = []
        for mood in c.base_moods:
            if not any(mood.lower() in m.lower() or m.lower() in mood.lower() for m in unique_moods):
                unique_moods.append(mood)
        mood_str = " and ".join(unique_moods[:2])
        if len(unique_moods) > 2:
            mood_str += f", {unique_moods[2]}"
        parts.append(mood_str)
    
    tempo_desc = _get_tempo_descriptor(c.tempo_final)
    parts.append(f"{tempo_desc} {c.tempo_final} BPM")
    
    technical = ["stereo"]
    if "ambient" in c.genre.lower():
        technical.append("spacious")
    parts.append(", ".join(technical))
    
    return ", ".join(parts)


def _assemble_prompt_minimal(c: PromptComponents) -> str:
    """Minimal prompt - just essential keywords."""
    elements = [
        c.genre,
        c.base_instruments[0] if c.base_instruments else "",
        c.base_moods[0] if c.base_moods else "",
    ]
    if c.texture_timbre:
        elements.append(c.texture_timbre[0])
    elements.extend([f"{c.tempo_final} BPM", "stereo"])
    return ", ".join(e for e in elements if e)


def _assemble_prompt_natural(c: PromptComponents) -> str:
    """Natural language prompt - more conversational."""
    mood_phrase = " and ".join(c.base_moods[:2]) if c.base_moods else "atmospheric"
    inst_phrase = " and ".join(c.base_instruments[:2]) if c.base_instruments else "synthesizers"
    tempo_desc = _get_tempo_descriptor(c.tempo_final)
    
    texture_phrase = ""
    if c.texture_timbre:
        texture_phrase = f" with {c.texture_timbre[0]} textures"
    elif c.texture_movement:
        texture_phrase = f", {c.texture_movement[0]}"
    
    return (
        f"A {mood_phrase} piece of {c.genre} music{texture_phrase} "
        f"featuring {inst_phrase}, at a {tempo_desc} {c.tempo_final} BPM tempo"
    )


# =============================================================================
# INTEGRATION FUNCTION
# =============================================================================

def build_prompt_from_selection(
    selection: dict,
    themes: List[str] = None,
    date_seed: date = None,
) -> PromptResult:
    """Build prompt from selection dict."""
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
