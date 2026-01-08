"""
MusicGen Archetypes for World Theme Music Player

This module defines the "World Mood Archetypes" - curated musical descriptors
optimized for Meta's MusicGen model. Each archetype represents a bathroom-safe
ambient mood that world news can map to.

Design Principles:
1. All archetypes produce ambient, bathroom-appropriate music
2. Descriptors are proven to work well with MusicGen
3. Archetypes can be blended for nuanced output
4. Intensity modifiers allow fine-tuning based on tension levels

Based on MusicGen research findings:
- Adjective + instrument combinations work best
- Combining musical + emotional moods is effective
- Explicit BPM improves consistency
- Comma-separated keywords are well understood
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class ArchetypeName(Enum):
    """Enumeration of available mood archetypes."""
    TRANQUIL_OPTIMISM = "tranquil_optimism"
    REFLECTIVE_CALM = "reflective_calm"
    GENTLE_TENSION = "gentle_tension"
    MELANCHOLIC_BEAUTY = "melancholic_beauty"
    CAUTIOUS_HOPE = "cautious_hope"
    SERENE_RESILIENCE = "serene_resilience"


@dataclass
class MusicDescriptor:
    """
    Structured music description optimized for MusicGen.
    
    Each field maps to elements that MusicGen understands well:
    - genre: Primary musical style (e.g., "ambient electronic")
    - instruments: List of adjective+instrument pairs
    - mood_musical: Technical musical qualities (e.g., "flowing", "atmospheric")
    - mood_emotional: Emotional qualities (e.g., "peaceful", "contemplative")
    - tempo_bpm: Explicit BPM with tempo descriptor
    - technical: Production qualities (e.g., "stereo", "reverb")
    """
    genre: str
    instruments: List[str]
    mood_musical: List[str]
    mood_emotional: List[str]
    tempo_bpm: str
    tempo_value: int  # Numeric BPM for blending calculations
    technical: List[str] = field(default_factory=lambda: ["stereo"])
    
    def to_prompt(self) -> str:
        """Convert descriptor to MusicGen-compatible prompt string."""
        parts = [self.genre]
        parts.extend(self.instruments)
        parts.extend(self.mood_musical)
        parts.extend(self.mood_emotional)
        parts.append(self.tempo_bpm)
        parts.extend(self.technical)
        return ", ".join(parts)


# =============================================================================
# ARCHETYPE DEFINITIONS
# =============================================================================

ARCHETYPES: Dict[ArchetypeName, MusicDescriptor] = {
    
    ArchetypeName.TRANQUIL_OPTIMISM: MusicDescriptor(
        genre="ambient electronic",
        instruments=[
            "soft synth pads",
            "gentle piano",
            "subtle chimes",
            "light bells"
        ],
        mood_musical=["flowing", "light", "melodic", "airy"],
        mood_emotional=["peaceful", "hopeful", "serene", "uplifting"],
        tempo_bpm="slow 65 BPM",
        tempo_value=65,
        technical=["stereo", "warm", "clean"]
    ),
    
    ArchetypeName.REFLECTIVE_CALM: MusicDescriptor(
        genre="ambient new age",
        instruments=[
            "flowing synth textures",
            "soft strings",
            "gentle pads",
            "nature sounds"
        ],
        mood_musical=["sustained", "atmospheric", "gentle", "spacious"],
        mood_emotional=["contemplative", "calm", "introspective", "meditative"],
        tempo_bpm="very slow 58 BPM",
        tempo_value=58,
        technical=["stereo", "spacious", "reverb"]
    ),
    
    ArchetypeName.GENTLE_TENSION: MusicDescriptor(
        genre="cinematic ambient",
        instruments=[
            "atmospheric pads",
            "subtle strings",
            "soft drones",
            "distant piano"
        ],
        mood_musical=["atmospheric", "layered", "evolving", "textural"],
        mood_emotional=["thoughtful", "uncertain", "bittersweet", "restrained"],
        tempo_bpm="slow 68 BPM",
        tempo_value=68,
        technical=["stereo", "reverb", "cinematic"]
    ),
    
    ArchetypeName.MELANCHOLIC_BEAUTY: MusicDescriptor(
        genre="ambient orchestral",
        instruments=[
            "expressive strings",
            "warm piano",
            "ethereal pads",
            "soft cello"
        ],
        mood_musical=["flowing", "swelling", "tender", "emotional"],
        mood_emotional=["melancholic", "nostalgic", "beautiful", "wistful"],
        tempo_bpm="slow 62 BPM",
        tempo_value=62,
        technical=["stereo", "cinematic", "warm"]
    ),
    
    ArchetypeName.CAUTIOUS_HOPE: MusicDescriptor(
        genre="ambient electronic",
        instruments=[
            "soft synths",
            "gentle bells",
            "flowing textures",
            "light arpeggios"
        ],
        mood_musical=["building", "delicate", "atmospheric", "subtle"],
        mood_emotional=["hopeful", "restrained", "peaceful", "anticipating"],
        tempo_bpm="slow 70 BPM",
        tempo_value=70,
        technical=["stereo", "clean", "bright"]
    ),
    
    ArchetypeName.SERENE_RESILIENCE: MusicDescriptor(
        genre="ambient post-rock",
        instruments=[
            "swelling strings",
            "soft guitar",
            "atmospheric synths",
            "gentle drums"
        ],
        mood_musical=["building", "expansive", "dynamic", "flowing"],
        mood_emotional=["calm", "determined", "uplifting", "grounded"],
        tempo_bpm="medium 75 BPM",
        tempo_value=75,
        technical=["stereo", "warm", "spacious"]
    ),
}


# =============================================================================
# COMPATIBILITY MATRIX FOR BLENDING
# =============================================================================

COMPATIBILITY_MATRIX: Dict[ArchetypeName, List[ArchetypeName]] = {
    ArchetypeName.TRANQUIL_OPTIMISM: [
        ArchetypeName.CAUTIOUS_HOPE,
        ArchetypeName.REFLECTIVE_CALM,
        ArchetypeName.SERENE_RESILIENCE
    ],
    ArchetypeName.REFLECTIVE_CALM: [
        ArchetypeName.CAUTIOUS_HOPE,
        ArchetypeName.SERENE_RESILIENCE,
        ArchetypeName.MELANCHOLIC_BEAUTY
    ],
    ArchetypeName.GENTLE_TENSION: [
        ArchetypeName.MELANCHOLIC_BEAUTY,
        ArchetypeName.CAUTIOUS_HOPE,
        ArchetypeName.REFLECTIVE_CALM
    ],
    ArchetypeName.MELANCHOLIC_BEAUTY: [
        ArchetypeName.GENTLE_TENSION,
        ArchetypeName.REFLECTIVE_CALM
    ],
    ArchetypeName.CAUTIOUS_HOPE: [
        ArchetypeName.TRANQUIL_OPTIMISM,
        ArchetypeName.GENTLE_TENSION,
        ArchetypeName.SERENE_RESILIENCE
    ],
    ArchetypeName.SERENE_RESILIENCE: [
        ArchetypeName.CAUTIOUS_HOPE,
        ArchetypeName.REFLECTIVE_CALM,
        ArchetypeName.TRANQUIL_OPTIMISM
    ],
}


# =============================================================================
# INTENSITY MODIFIERS
# =============================================================================

INTENSITY_MODIFIERS = {
    "low": {
        "instrument_adjectives": ["soft", "gentle", "subtle", "light", "delicate"],
        "mood_adjectives": ["peaceful", "calm", "serene", "quiet"],
        "tempo_modifier": -3
    },
    "medium": {
        "instrument_adjectives": ["flowing", "warm", "atmospheric", "layered"],
        "mood_adjectives": ["contemplative", "thoughtful", "balanced"],
        "tempo_modifier": 0
    },
    "high": {
        "instrument_adjectives": ["deep", "layered", "evolving", "rich", "textural"],
        "mood_adjectives": ["complex", "nuanced", "introspective", "profound"],
        "tempo_modifier": +3
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_archetype(name: ArchetypeName) -> MusicDescriptor:
    """Get archetype descriptor by name."""
    return ARCHETYPES[name]


def get_compatible_archetypes(primary: ArchetypeName) -> List[ArchetypeName]:
    """Get list of archetypes compatible for blending with primary."""
    return COMPATIBILITY_MATRIX.get(primary, [])


def is_compatible(primary: ArchetypeName, secondary: ArchetypeName) -> bool:
    """Check if two archetypes are compatible for blending."""
    return secondary in COMPATIBILITY_MATRIX.get(primary, [])


def get_intensity_level(tension: float) -> str:
    """Map tension value (0-1) to intensity level."""
    if tension < 0.3:
        return "low"
    elif tension < 0.6:
        return "medium"
    else:
        return "high"


def get_intensity_modifiers(tension: float) -> dict:
    """Get intensity modifiers based on tension level."""
    level = get_intensity_level(tension)
    return INTENSITY_MODIFIERS[level]


def list_all_archetypes() -> List[str]:
    """Return list of all archetype names as strings."""
    return [a.value for a in ArchetypeName]
