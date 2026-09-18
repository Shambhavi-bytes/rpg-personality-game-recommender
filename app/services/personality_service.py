"""
Personality scoring service.

Tracks Big Five scores silently as the user makes choices, using Flask
session storage. Routes only call the public functions below — they
never access session data directly.
"""

from flask import session

# Session key under which the score dictionary is stored.
_SESSION_KEY = "personality_scores"

# The five Big Five traits, used to build a consistent starting structure.
BIG_FIVE_TRAITS = [
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
]


def reset_scores():
    """
    Reset all Big Five scores to zero and store them in the session.

    Called when a new adventure begins, so a returning user doesn't
    carry over scores from a previous playthrough.
    """
    session[_SESSION_KEY] = {trait: 0 for trait in BIG_FIVE_TRAITS}


def get_scores():
    """
    Return the current Big Five scores from the session.

    If no scores exist yet (e.g. session expired, or accessed before
    reset_scores() was called), initialise them first rather than
    raising an error.
    """
    if _SESSION_KEY not in session:
        reset_scores()
    return session[_SESSION_KEY]


def update_scores(score_delta):
    """
    Apply a score update after a narrative choice.

    score_delta is a dict like {"openness": 1}, taken directly from the
    chosen choice's "score" field in narrative.json. This function does
    not know or care about narrative structure — it only adds values to
    the existing scores.
    """
    scores = get_scores()

    for trait, value in score_delta.items():
        if trait in scores:
            scores[trait] += value

    # Flask sessions don't automatically detect changes to nested dicts,
    # so the session must be explicitly marked as modified to ensure the
    # updated scores are saved.
    session[_SESSION_KEY] = scores