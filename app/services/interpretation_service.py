"""
Personality interpretation service.

Converts accumulated Big Five scores into a High/Moderate/Low
interpretation per trait and a matched RPG archetype, using a
deterministic rule-based prototype informed by the literature review.

This is NOT a validated psychometric classifier. The exact archetype
weighting is a prototype design decision, documented as such in the
dissertation methodology.
"""

# Archetype definitions. Primary trait carries weight 2, secondary trait
# weight 1. Direction "high" means a higher raw trait score increases
# compatibility; "low" means a lower raw score increases compatibility.
_ARCHETYPES = {
    "Mage": {
        "primary": ("openness", "high"),
        "secondary": ("conscientiousness", "high"),
        "description": "Curious and imaginative, drawn to exploring unfamiliar ideas with a careful, deliberate approach.",
    },
    "Ranger": {
        "primary": ("openness", "high"),
        "secondary": ("extraversion", "low"),
        "description": "Independent and exploratory, comfortable venturing into unfamiliar territory alone.",
    },
    "Rogue": {
        "primary": ("extraversion", "high"),
        "secondary": ("openness", "high"),
        "description": "Socially confident and adaptable, quick to embrace unconventional approaches.",
    },
    "Paladin": {
        "primary": ("agreeableness", "high"),
        "secondary": ("conscientiousness", "high"),
        "description": "Cooperative and dependable, committed to helping others and following through on responsibilities.",
    },
    "Fighter": {
        "primary": ("conscientiousness", "high"),
        "secondary": ("openness", "low"),
        "description": "Disciplined and persistent, favouring direct, tried-and-tested approaches to problems.",
    },
}

# Fixed priority order, used only to break compatibility-score ties.
# Kept as an explicit list rather than relying on dict ordering, so the
# tie-break rule is visible on its own rather than an implementation detail.
_ARCHETYPE_PRIORITY = ["Mage", "Ranger", "Rogue", "Paladin", "Fighter"]

# Neuroticism has no entry in _ARCHETYPES and is never read by
# _compatibility_score() — by design, it plays no part in archetype
# matching, only in the profile shown to the user.


def _trait_level(score):
    """Convert a raw trait score (-3 to +3) into High/Moderate/Low."""
    if score >= 2:
        return "High"
    if score <= -2:
        return "Low"
    return "Moderate"


def _compatibility_score(archetype_def, scores):
    """
    Compute one archetype's compatibility score for the given traits.

    For a "low" direction trait, the score is negated before weighting,
    so a lower raw score produces a higher compatibility contribution.
    """
    total = 0

    trait, direction = archetype_def["primary"]
    value = scores[trait] if direction == "high" else -scores[trait]
    total += 2 * value

    trait, direction = archetype_def["secondary"]
    value = scores[trait] if direction == "high" else -scores[trait]
    total += 1 * value

    return total


def determine_archetype(scores):
    """
    Return the best-matching archetype name for the given Big Five scores.

    Archetypes are checked in the fixed priority order, and the current
    best is only replaced by a STRICTLY higher score. This means the
    first archetype in priority order automatically wins any tie, which
    is what satisfies the deterministic tie-break requirement.
    """
    best_name = None
    best_score = None

    for name in _ARCHETYPE_PRIORITY:
        score = _compatibility_score(_ARCHETYPES[name], scores)
        if best_score is None or score > best_score:
            best_score = score
            best_name = name

    return best_name


def build_profile(scores):
    """
    Build the structured personality profile used by the results page.

    Returns the matched archetype, its description, and each trait's
    raw score with its High/Moderate/Low interpretation.
    """
    archetype_name = determine_archetype(scores)
    archetype = _ARCHETYPES[archetype_name]

    traits = {
        trait: {"score": value, "level": _trait_level(value)}
        for trait, value in scores.items()
    }

    return {
        "archetype": archetype_name,
        "description": archetype["description"],
        "traits": traits,
    }