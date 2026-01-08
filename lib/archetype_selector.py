"""
Archetype Selector Module

Maps structured news analysis to mood archetypes using rule-based scoring.
Implements "Smart Medium" blending: primary archetype + compatible secondary.

Input: NewsAnalysis
Output: ArchetypeSelection with primary, optional secondary, and scores
"""

import math
from typing import Optional, Dict, List
from dataclasses import dataclass
from loguru import logger

from lib.archetypes import (
    ArchetypeName,
    ARCHETYPES,
    get_archetype,
    is_compatible,
    get_intensity_level,
)


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
    score: float
    valence_match: float
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
    intensity_level: str
    blend_ratio: Optional[float]
    
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

@dataclass
class ArchetypeProfile:
    """Ideal analysis profile for an archetype."""
    valence_center: float
    valence_tolerance: float
    tension_center: float
    tension_tolerance: float
    hope_center: float
    hope_tolerance: float
    preferred_energy: List[str]


ARCHETYPE_PROFILES: Dict[ArchetypeName, ArchetypeProfile] = {
    ArchetypeName.TRANQUIL_OPTIMISM: ArchetypeProfile(
        valence_center=0.6, valence_tolerance=0.4,
        tension_center=0.2, tension_tolerance=0.3,
        hope_center=0.8, hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    ArchetypeName.REFLECTIVE_CALM: ArchetypeProfile(
        valence_center=0.2, valence_tolerance=0.4,
        tension_center=0.2, tension_tolerance=0.3,
        hope_center=0.5, hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    ArchetypeName.GENTLE_TENSION: ArchetypeProfile(
        valence_center=-0.1, valence_tolerance=0.4,
        tension_center=0.6, tension_tolerance=0.3,
        hope_center=0.4, hope_tolerance=0.3,
        preferred_energy=["medium", "high"]
    ),
    ArchetypeName.MELANCHOLIC_BEAUTY: ArchetypeProfile(
        valence_center=-0.4, valence_tolerance=0.4,
        tension_center=0.5, tension_tolerance=0.3,
        hope_center=0.3, hope_tolerance=0.3,
        preferred_energy=["low", "medium"]
    ),
    ArchetypeName.CAUTIOUS_HOPE: ArchetypeProfile(
        valence_center=0.2, valence_tolerance=0.4,
        tension_center=0.5, tension_tolerance=0.3,
        hope_center=0.6, hope_tolerance=0.3,
        preferred_energy=["medium"]
    ),
    ArchetypeName.SERENE_RESILIENCE: ArchetypeProfile(
        valence_center=0.3, valence_tolerance=0.4,
        tension_center=0.4, tension_tolerance=0.3,
        hope_center=0.7, hope_tolerance=0.3,
        preferred_energy=["medium", "high"]
    ),
}


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_dimension_match(value: float, center: float, tolerance: float) -> float:
    """Calculate how well a value matches a target center with given tolerance."""
    distance = abs(value - center)
    normalized_distance = distance / tolerance if tolerance > 0 else distance
    score = math.exp(-normalized_distance ** 2)
    return max(0.0, min(1.0, score))


def calculate_energy_match(energy: str, preferred: List[str]) -> float:
    """Calculate energy level match."""
    if energy in preferred:
        return 1.0
    
    energy_order = ["low", "medium", "high"]
    if energy not in energy_order:
        return 0.5
    
    energy_idx = energy_order.index(energy)
    min_distance = float('inf')
    
    for pref in preferred:
        if pref in energy_order:
            pref_idx = energy_order.index(pref)
            min_distance = min(min_distance, abs(energy_idx - pref_idx))
    
    if min_distance == 1:
        return 0.6
    elif min_distance == 2:
        return 0.3
    return 0.5


def score_archetype(analysis: NewsAnalysis, archetype: ArchetypeName) -> ArchetypeScore:
    """Score how well an analysis matches an archetype profile."""
    profile = ARCHETYPE_PROFILES[archetype]
    
    valence_match = calculate_dimension_match(
        analysis.emotional_valence, profile.valence_center, profile.valence_tolerance
    )
    tension_match = calculate_dimension_match(
        analysis.tension_level, profile.tension_center, profile.tension_tolerance
    )
    hope_match = calculate_dimension_match(
        analysis.hope_factor, profile.hope_center, profile.hope_tolerance
    )
    energy_match = calculate_energy_match(analysis.energy_level, profile.preferred_energy)
    
    weights = {"valence": 0.30, "tension": 0.25, "hope": 0.30, "energy": 0.15}
    
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
    scores = [score_archetype(analysis, archetype) for archetype in ArchetypeName]
    scores.sort(key=lambda s: s.score, reverse=True)
    return scores


# =============================================================================
# SELECTION LOGIC
# =============================================================================

SECONDARY_THRESHOLD_RATIO = 0.70
SECONDARY_MIN_SCORE = 0.50


def select_archetypes(analysis: NewsAnalysis) -> ArchetypeSelection:
    """
    Select primary and optional secondary archetype based on analysis.
    
    Rules:
    1. Primary = highest scoring archetype
    2. Secondary = second highest IF compatible and score thresholds met
    3. Blend ratio based on relative scores
    """
    all_scores = score_all_archetypes(analysis)
    
    primary_score = all_scores[0]
    primary = primary_score.archetype
    
    secondary = None
    secondary_score_obj = None
    blend_ratio = None
    
    for candidate in all_scores[1:]:
        if not is_compatible(primary, candidate.archetype):
            continue
        
        ratio = candidate.score / primary_score.score if primary_score.score > 0 else 0
        
        if ratio >= SECONDARY_THRESHOLD_RATIO and candidate.score >= SECONDARY_MIN_SCORE:
            secondary = candidate.archetype
            secondary_score_obj = candidate
            total = primary_score.score + candidate.score
            blend_ratio = primary_score.score / total if total > 0 else 1.0
            break
    
    intensity_level = get_intensity_level(analysis.tension_level)
    
    selection = ArchetypeSelection(
        primary=primary,
        primary_score=primary_score.score,
        secondary=secondary,
        secondary_score=secondary_score_obj.score if secondary_score_obj else None,
        all_scores=all_scores,
        intensity_level=intensity_level,
        blend_ratio=round(blend_ratio, 2) if blend_ratio else None
    )
    
    # Log selection
    logger.info(f"[Selector] Primary: {primary.value} (score: {primary_score.score:.3f})")
    if secondary:
        logger.info(f"[Selector] Secondary: {secondary.value} (score: {secondary_score_obj.score:.3f})")
        logger.info(f"[Selector] Blend ratio: {blend_ratio:.0%} / {1-blend_ratio:.0%}")
    logger.info(f"[Selector] Intensity: {intensity_level}")
    
    return selection
