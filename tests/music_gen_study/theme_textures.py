"""
Theme Textures Library - Step 03a

Maps news themes to musical texture descriptors for nuanced prompt generation.
Provides timbral, movement, and harmonic coloring based on dominant themes.

This adds the "color" layer on top of archetype "structure".
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import random
from datetime import date
import hashlib


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ThemeTexture:
    """Musical texture descriptors for a theme."""
    timbre: List[str]      # Sound quality: digital, organic, warm, crystalline
    movement: List[str]    # How it flows: pulsing, swelling, breathing, static
    harmonic: List[str]    # Tonal character: minor, modal, suspended, bright
    
    def get_random_sample(self, seed: int = None) -> dict:
        """Get one descriptor from each category with optional seed."""
        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random
        
        return {
            "timbre": rng.choice(self.timbre) if self.timbre else None,
            "movement": rng.choice(self.movement) if self.movement else None,
            "harmonic": rng.choice(self.harmonic) if self.harmonic else None,
        }


@dataclass
class TextureBlend:
    """Blended texture from multiple themes."""
    timbre_words: List[str]
    movement_words: List[str]
    harmonic_words: List[str]
    source_themes: List[str]
    
    def to_prompt_fragments(self) -> List[str]:
        """Convert to prompt-ready fragments."""
        fragments = []
        
        # Timbre becomes adjectives for instruments
        if self.timbre_words:
            fragments.extend(self.timbre_words[:2])
        
        # Movement becomes texture description
        if self.movement_words:
            fragments.append(self.movement_words[0])
        
        # Harmonic becomes mood modifier
        if self.harmonic_words:
            fragments.append(self.harmonic_words[0])
        
        return fragments


# =============================================================================
# THEME TEXTURE LIBRARY
# =============================================================================

THEME_TEXTURES: Dict[str, ThemeTexture] = {
    
    # =========================================================================
    # HUMAN & SOCIAL
    # =========================================================================
    
    "conflict": ThemeTexture(
        timbre=["shadowed", "distant", "veiled", "muted", "heavy"],
        movement=["unsettled", "shifting", "restless", "turbulent"],
        harmonic=["minor undertones", "dissonant hints", "unresolved", "tense"],
    ),
    
    "war": ThemeTexture(
        timbre=["distant", "industrial", "metallic", "dark"],
        movement=["marching", "relentless", "pounding"],
        harmonic=["minor", "diminished", "stark"],
    ),
    
    "peace": ThemeTexture(
        timbre=["open", "sunlit", "clear", "radiant", "luminous"],
        movement=["breathing", "gentle swells", "expansive", "releasing"],
        harmonic=["major", "resolved", "consonant", "bright"],
    ),
    
    "politics": ThemeTexture(
        timbre=["complex", "layered", "textured", "dense", "woven"],
        movement=["measured", "deliberate", "careful", "calculated"],
        harmonic=["modal", "ambiguous", "shifting", "nuanced"],
    ),
    
    "humanitarian": ThemeTexture(
        timbre=["human", "communal", "embracing", "tender", "connected"],
        movement=["gathering", "uplifting", "joining", "rising together"],
        harmonic=["hopeful", "warm major", "supportive", "unified"],
    ),
    
    "community": ThemeTexture(
        timbre=["warm", "familiar", "grounded", "intimate"],
        movement=["rhythmic", "shared pulse", "collective"],
        harmonic=["folk-like", "simple", "honest"],
    ),
    
    "tragedy": ThemeTexture(
        timbre=["somber", "hollow", "echoing", "fragile"],
        movement=["slow descent", "fading", "grieving"],
        harmonic=["minor", "lamenting", "sorrowful"],
    ),
    
    "celebration": ThemeTexture(
        timbre=["bright", "sparkling", "vibrant", "festive"],
        movement=["dancing", "joyful", "energetic"],
        harmonic=["major", "triumphant", "elated"],
    ),
    
    # =========================================================================
    # TECHNOLOGY & SCIENCE
    # =========================================================================
    
    "technology": ThemeTexture(
        timbre=["digital", "crystalline", "precise", "clean", "synthetic"],
        movement=["pulsing", "sequenced", "algorithmic", "gridded"],
        harmonic=["electronic", "processed", "pure tones"],
    ),
    
    "science": ThemeTexture(
        timbre=["exploratory", "vast", "curious", "analytical", "discovering"],
        movement=["expanding", "probing", "systematic", "building"],
        harmonic=["open intervals", "spacious", "questioning"],
    ),
    
    "AI": ThemeTexture(
        timbre=["synthetic", "evolving", "emergent", "neural"],
        movement=["learning", "adapting", "processing"],
        harmonic=["algorithmic", "generative", "unpredictable"],
    ),
    
    "space": ThemeTexture(
        timbre=["cosmic", "infinite", "stellar", "ethereal", "void"],
        movement=["drifting", "orbiting", "floating", "weightless"],
        harmonic=["vast", "suspended", "otherworldly"],
    ),
    
    "medical": ThemeTexture(
        timbre=["clinical", "sterile", "precise", "careful"],
        movement=["steady pulse", "monitoring", "rhythmic"],
        harmonic=["neutral", "functional", "measured"],
    ),
    
    # =========================================================================
    # NATURE & ENVIRONMENT
    # =========================================================================
    
    "environment": ThemeTexture(
        timbre=["organic", "earthen", "natural", "living", "verdant"],
        movement=["flowing", "cyclical", "seasonal", "breathing"],
        harmonic=["pastoral", "grounded", "rooted"],
    ),
    
    "climate": ThemeTexture(
        timbre=["elemental", "weathered", "shifting", "atmospheric"],
        movement=["building", "receding", "storming", "clearing"],
        harmonic=["evolving", "transforming", "unstable"],
    ),
    
    "nature": ThemeTexture(
        timbre=["acoustic", "woody", "rustling", "living"],
        movement=["wind-like", "water-like", "organic flow"],
        harmonic=["natural", "pentatonic", "folk"],
    ),
    
    "disaster": ThemeTexture(
        timbre=["crushing", "overwhelming", "raw", "primal"],
        movement=["sudden", "chaotic", "destructive"],
        harmonic=["dissonant", "crashing", "uncontrolled"],
    ),
    
    "ocean": ThemeTexture(
        timbre=["deep", "flowing", "vast", "tidal"],
        movement=["waves", "surging", "ebbing"],
        harmonic=["blue", "mysterious", "ancient"],
    ),
    
    # =========================================================================
    # ECONOMY & SYSTEMS
    # =========================================================================
    
    "economy": ThemeTexture(
        timbre=["structured", "measured", "balanced", "mechanical"],
        movement=["steady", "rhythmic", "cycling", "trading"],
        harmonic=["neutral", "functional", "ordered"],
    ),
    
    "finance": ThemeTexture(
        timbre=["precise", "calculated", "sharp", "metallic"],
        movement=["ticking", "fluctuating", "nervous"],
        harmonic=["tense", "anticipating", "volatile"],
    ),
    
    "markets": ThemeTexture(
        timbre=["electric", "buzzing", "active", "rapid"],
        movement=["rising", "falling", "volatile"],
        harmonic=["unstable", "shifting", "reactive"],
    ),
    
    # =========================================================================
    # HEALTH & WELLBEING
    # =========================================================================
    
    "health": ThemeTexture(
        timbre=["healing", "restorative", "warm", "nurturing"],
        movement=["gentle pulse", "recovering", "strengthening"],
        harmonic=["consonant", "soothing", "therapeutic"],
    ),
    
    "wellness": ThemeTexture(
        timbre=["pure", "clean", "refreshing", "vital"],
        movement=["breathing", "centering", "balancing"],
        harmonic=["harmonious", "aligned", "peaceful"],
    ),
    
    "disease": ThemeTexture(
        timbre=["troubled", "weakened", "struggling"],
        movement=["labored", "fighting", "persisting"],
        harmonic=["strained", "discordant", "recovering"],
    ),
    
    # =========================================================================
    # CULTURE & ARTS
    # =========================================================================
    
    "culture": ThemeTexture(
        timbre=["rich", "layered", "storied", "traditional"],
        movement=["ceremonial", "ritualistic", "expressive"],
        harmonic=["heritage", "ancestral", "timeless"],
    ),
    
    "arts": ThemeTexture(
        timbre=["creative", "expressive", "colorful", "imaginative"],
        movement=["flowing", "interpretive", "free"],
        harmonic=["artistic", "experimental", "inspired"],
    ),
    
    "sports": ThemeTexture(
        timbre=["energetic", "powerful", "athletic", "driving"],
        movement=["competitive", "racing", "pushing"],
        harmonic=["triumphant", "determined", "intense"],
    ),
    
    "entertainment": ThemeTexture(
        timbre=["playful", "bright", "engaging", "fun"],
        movement=["bouncing", "lively", "animated"],
        harmonic=["catchy", "upbeat", "accessible"],
    ),
    
    # =========================================================================
    # GENERIC / FALLBACK
    # =========================================================================
    
    "general": ThemeTexture(
        timbre=["balanced", "neutral", "even"],
        movement=["steady", "consistent"],
        harmonic=["stable", "centered"],
    ),
}


# =============================================================================
# THEME ALIASES (map variations to canonical themes)
# =============================================================================

THEME_ALIASES: Dict[str, str] = {
    # Conflict cluster
    "military": "conflict",
    "violence": "conflict",
    "tension": "conflict",
    "crisis": "conflict",
    "warfare": "war",
    "fighting": "war",
    
    # Peace cluster
    "diplomacy": "peace",
    "treaty": "peace",
    "ceasefire": "peace",
    "reconciliation": "peace",
    
    # Politics cluster
    "government": "politics",
    "election": "politics",
    "policy": "politics",
    "legislation": "politics",
    "democracy": "politics",
    
    # Technology cluster
    "tech": "technology",
    "digital": "technology",
    "innovation": "technology",
    "computing": "technology",
    "artificial intelligence": "AI",
    "machine learning": "AI",
    
    # Science cluster
    "research": "science",
    "discovery": "science",
    "breakthrough": "science",
    "astronomy": "space",
    "nasa": "space",
    
    # Environment cluster
    "weather": "climate",
    "pollution": "environment",
    "sustainability": "environment",
    "green": "environment",
    "earthquake": "disaster",
    "flood": "disaster",
    "hurricane": "disaster",
    "wildfire": "disaster",
    
    # Economy cluster
    "business": "economy",
    "trade": "economy",
    "inflation": "finance",
    "stocks": "markets",
    "investment": "finance",
    
    # Health cluster
    "medicine": "health",
    "healthcare": "health",
    "pandemic": "disease",
    "virus": "disease",
    "vaccine": "health",
    
    # Social cluster
    "refugee": "humanitarian",
    "aid": "humanitarian",
    "charity": "humanitarian",
    "poverty": "humanitarian",
    "local": "community",
    "neighborhood": "community",
}


# =============================================================================
# TEXTURE BLENDING
# =============================================================================

def resolve_theme(theme: str) -> str:
    """Resolve theme to canonical name."""
    theme_lower = theme.lower().strip()
    
    # Check aliases first
    if theme_lower in THEME_ALIASES:
        return THEME_ALIASES[theme_lower]
    
    # Check if it's already a known theme
    if theme_lower in THEME_TEXTURES:
        return theme_lower
    
    # Fallback to general
    return "general"


def get_texture(theme: str) -> ThemeTexture:
    """Get texture for a theme (with alias resolution)."""
    canonical = resolve_theme(theme)
    return THEME_TEXTURES.get(canonical, THEME_TEXTURES["general"])


def blend_textures(
    themes: List[str],
    date_seed: Optional[date] = None,
    max_words: int = 2,
) -> TextureBlend:
    """
    Blend textures from multiple themes.
    
    Uses date as seed for consistent daily variation.
    """
    if not themes:
        themes = ["general"]
    
    # Create seed from date
    if date_seed:
        seed_str = date_seed.isoformat()
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    else:
        seed = None
    
    rng = random.Random(seed) if seed else random
    
    # Collect all texture words
    all_timbre = []
    all_movement = []
    all_harmonic = []
    resolved_themes = []
    
    for theme in themes[:5]:  # Max 5 themes
        resolved = resolve_theme(theme)
        resolved_themes.append(resolved)
        texture = THEME_TEXTURES.get(resolved, THEME_TEXTURES["general"])
        
        all_timbre.extend(texture.timbre)
        all_movement.extend(texture.movement)
        all_harmonic.extend(texture.harmonic)
    
    # Remove duplicates while preserving some order
    def unique_shuffle(lst: List[str], rng) -> List[str]:
        unique = list(dict.fromkeys(lst))  # Remove dupes, keep order
        rng.shuffle(unique)
        return unique
    
    timbre_pool = unique_shuffle(all_timbre, rng)
    movement_pool = unique_shuffle(all_movement, rng)
    harmonic_pool = unique_shuffle(all_harmonic, rng)
    
    return TextureBlend(
        timbre_words=timbre_pool[:max_words],
        movement_words=movement_pool[:max_words],
        harmonic_words=harmonic_pool[:1],  # Usually just one harmonic hint
        source_themes=resolved_themes,
    )


# =============================================================================
# DAILY VARIATION
# =============================================================================

@dataclass
class DailyVariation:
    """Controls day-to-day variety in prompts."""
    instrument_rotation: int      # Which instrument variant to prefer
    mood_shuffle_seed: int        # Seed for mood ordering
    texture_emphasis: str         # "timbre", "movement", or "harmonic"
    tempo_nudge: int              # Small BPM adjustment (-2 to +2)
    
    @classmethod
    def from_date(cls, d: date = None) -> "DailyVariation":
        """Generate variation parameters from date."""
        if d is None:
            d = date.today()
        
        # Create deterministic seed from date
        seed_str = d.isoformat()
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        return cls(
            instrument_rotation=rng.randint(0, 2),
            mood_shuffle_seed=seed,
            texture_emphasis=rng.choice(["timbre", "movement", "harmonic"]),
            tempo_nudge=rng.randint(-2, 3),  # Slight bias toward faster
        )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def list_all_themes() -> List[str]:
    """List all known themes."""
    return sorted(THEME_TEXTURES.keys())


def list_all_aliases() -> Dict[str, str]:
    """List all theme aliases."""
    return THEME_ALIASES.copy()


def get_theme_preview(theme: str) -> str:
    """Get a preview string for a theme's textures."""
    texture = get_texture(theme)
    return (
        f"{theme}: "
        f"timbre=[{', '.join(texture.timbre[:2])}...] "
        f"movement=[{', '.join(texture.movement[:2])}...] "
        f"harmonic=[{', '.join(texture.harmonic[:2])}...]"
    )


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("Theme Textures Library")
    print("=" * 60)
    
    # Show some theme previews
    print("\nSample themes:")
    for theme in ["conflict", "peace", "technology", "environment", "economy"]:
        print(f"  {get_theme_preview(theme)}")
    
    # Test blending
    print("\n" + "=" * 60)
    print("Texture Blending Test")
    print("=" * 60)
    
    test_themes = ["technology", "conflict", "economy"]
    print(f"\nThemes: {test_themes}")
    
    blend = blend_textures(test_themes, date_seed=date.today())
    print(f"Resolved: {blend.source_themes}")
    print(f"Timbre: {blend.timbre_words}")
    print(f"Movement: {blend.movement_words}")
    print(f"Harmonic: {blend.harmonic_words}")
    print(f"Prompt fragments: {blend.to_prompt_fragments()}")
    
    # Test daily variation
    print("\n" + "=" * 60)
    print("Daily Variation Test")
    print("=" * 60)
    
    for i in range(3):
        d = date(2026, 1, 7 + i)
        var = DailyVariation.from_date(d)
        print(f"\n{d}:")
        print(f"  Instrument rotation: {var.instrument_rotation}")
        print(f"  Texture emphasis: {var.texture_emphasis}")
        print(f"  Tempo nudge: {var.tempo_nudge:+d} BPM")
