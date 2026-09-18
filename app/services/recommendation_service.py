"""
Recommendation service.

Scores the game catalogue against the user's Big Five profile using
literature-informed genre relationships (Peever, Johnson & Gardner, 2012),
operationalised against the actual genre vocabulary available in
games_clean.csv.

Several literature-reported relationships could not be represented
without broadening or coarsening the dataset's genre categories, and are
therefore intentionally absent from this service rather than included as
dormant code. These are documented in the dissertation's methodology/
limitations section, not here:

 Openness: Platform
 Conscientiousness: Flight Simulation, Fighting
 Extraversion: Party, Music, Action-RPG, Turn-Based Strategy, Real-Time Strategy

The +1/-1 weights below are prototype implementation weights chosen for
transparency and consistency with the rest of the project's scoring
(Module 2B). They are NOT empirical effect sizes taken from Peever et al.

FALLBACK (added after pre-evaluation review):
Approximately 18.7% of the theoretical Big Five score space (every
combination where Openness, Conscientiousness, and Extraversion are all
<= 0) produces zero positive-scoring games under the rules above, since
every scoring rule requires one of those three traits to be > 0. When
this happens, a separate, deterministic, personality-independent
fallback selects 5 genre-diverse games from the catalogue instead. The
fallback makes no personality claim and is not part of the literature-
informed research layer - it exists purely so a participant is never
shown zero games. Each returned game carries a "source" field
("personality" or "fallback") so callers/templates can distinguish the
two cases without guessing.
"""

import csv
import os
from flask import current_app

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "games_clean.csv")

_games_cache = None  # in-memory cache, loaded once, same pattern as narrative_service


def _load_games():
    """
    Load games_clean.csv into memory the first time it's needed.

    Each game's Genres field is pre-split into a set for fast membership
    checks (e.g. "is Sports in this game's genres?") instead of re-parsing
    the raw string on every scoring call. AppID is kept as a string field
    so the fallback selection can sort by it deterministically.
    """
    global _games_cache
    if _games_cache is None:
        games = []
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                genre_field = row.get("Genres", "") or ""
                genres = {g.strip() for g in genre_field.split(",") if g.strip()}
                games.append({
                    "appid": row.get("AppID", "").strip(),
                    "name": row.get("Name", "").strip(),
                    "website": row.get("Website", "").strip(),
                    "genres": genres,
                })
        _games_cache = games
    return _games_cache


def _score_game(game, scores):
    """
    Score a single game against the user's Big Five scores.

    Only the literature relationships that could be operationalised
    against this dataset's genre vocabulary are checked here (see the
    module docstring for what was excluded and why).

    UNCHANGED from the approved Module 4B methodology.
    """
    total = 0
    genres = game["genres"]

    # Openness: literature category "Action-Adventure" operationalised as
    # requiring BOTH "Action" AND "Adventure" present on the same game -
    # matching only one does not qualify.
    if scores["openness"] > 0 and "Action" in genres and "Adventure" in genres:
        total += 1

    # Conscientiousness
    if scores["conscientiousness"] > 0:
        if "Sports" in genres:      # literature: "Sport"
            total += 1
        if "Racing" in genres:
            total += 1
        if "Simulation" in genres:
            total += 1

    # Extraversion (positive relationships)
    if scores["extraversion"] > 0:
        if "Casual" in genres:
            total += 1
        # Extraversion (negative relationships)
        if "RPG" in genres:
            total -= 1
        if "Massively Multiplayer" in genres:   # literature: "MMORPG"
            total -= 1

    return total


def _fallback_games(count):
    """
    Deterministic, personality-independent fallback selection.

    Used ONLY when personality-based scoring produces zero eligible
    games. Makes no reference to Big Five scores or genre-trait
    relationships - it exists purely to guarantee a usable participant
    experience, not as a research claim.

    Selection rule: walk the catalogue sorted by AppID ascending (a
    fixed, deterministic order), and pick the first game encountered
    that introduces at least one genre not yet represented in the
    selection, until `count` games have been chosen. This guarantees
    genre variety among the fallback games without ranking, scoring,
    or claiming any personality relationship.
    """
    games = _load_games()
    ordered = sorted(
        games,
        key=lambda g: int(g["appid"]) if g["appid"].isdigit() else 0
    )

    selected = []
    covered_genres = set()

    for game in ordered:
        if len(selected) >= count:
            break
        if not game["genres"]:
            continue
        if game["genres"] - covered_genres:  # introduces at least one new genre
            selected.append(game)
            covered_genres |= game["genres"]

    return selected


def get_recommendations(scores):
    """
    Return up to `count` games for the given Big Five scores.

    Normal case: games with a personality-based score strictly greater
    than 0, ranked highest first, alphabetical tie-break. Each entry
    has "source": "personality".

    Fallback case: if no game scores above 0 for this profile (see
    module docstring), returns 5 deterministic genre-diverse games
    instead, each with "source": "fallback" and no personality score.
    """
    games = _load_games()
    count = current_app.config.get("RECOMMENDATION_COUNT", 5)

    scored_games = []
    for game in games:
        score = _score_game(game, scores)
        if score <= 0:
            continue  # not eligible - see eligibility rule (Module 4B)
        scored_games.append({
            "name": game["name"],
            "score": score,
            "genres": sorted(game["genres"]),
            "website": game["website"],
            "source": "personality",
        })

    if scored_games:
        # Sort by score descending, then name ascending - the name sort
        # provides the deterministic tie-break agreed for equal scores.
        scored_games.sort(key=lambda g: (-g["score"], g["name"]))
        return scored_games[:count]

    # No positive-scoring games for this profile - use the deterministic
    # genre-diverse fallback instead of returning an empty list.
    fallback = _fallback_games(count)
    return [
        {
            "name": game["name"],
            "score": None,
            "genres": sorted(game["genres"]),
            "website": game["website"],
            "source": "fallback",
        }
        for game in fallback
    ]