"""
Narrative routes (Blueprint).

Handles:
- Homepage with "Begin Adventure" button
- Displaying a narrative scene 
- Processing a player's choice and moving to the next scene

This module is responsible ONLY for navigation through the narrative.
Personality scoring is delegated entirely to personality_service.
This file never reads or writes session data directly.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    abort,
)

# Import helper functions from the service layer.
# The routes never access the JSON file directly.
from app.services.narrative_service import (
    get_scene,
    get_start_scene_id,
    mark_assessment_complete,
    mark_assessment_incomplete,
    is_assessment_complete,
)

# Import helper functions from the personality service.
# The routes never touch Flask session data directly.
from app.services.personality_service import reset_scores, update_scores, get_scores

from app.services.interpretation_service import build_profile

from app.services.recommendation_service import get_recommendations

from app.services.llm_service import generate_character_profile

# Blueprint keeps all narrative-related routes together and prevents them
# from being mixed with future modules (recommendation, evaluation, etc.)
narrative_bp = Blueprint("narrative", __name__)


@narrative_bp.route("/")
def home():
    """
    Display the application's landing page.
    """
    return render_template("home.html")


@narrative_bp.route("/begin")
def begin():
    """
    Start the adventure by resetting personality scores and redirecting
    the user to the first scene.
    """
    reset_scores()
    mark_assessment_incomplete()

    return redirect(
        url_for(
            "narrative.show_scene",
            scene_id=get_start_scene_id()
        )
    )


@narrative_bp.route("/scene/<scene_id>")
def show_scene(scene_id):
    """
    Display a narrative scene.

    The scene is retrieved from the narrative service using its ID.
    If the scene does not exist, return a 404 error.
    """
    scene = get_scene(scene_id)

    if scene is None:
        abort(404)

    if scene_id == "s_end":
        mark_assessment_complete()

    return render_template(
        "scene.html",
        scene_id=scene_id,
        scene=scene
    )


@narrative_bp.route("/scene/<scene_id>/choose", methods=["POST"])
def choose(scene_id):
    """
    Process a player's choice, update personality scores, and redirect
    the user to the next narrative scene.
    """

    scene = get_scene(scene_id)

    if scene is None:
        abort(404)

    choice_index = request.form.get("choice_index", type=int)

    if (
        choice_index is None
        or choice_index < 0
        or choice_index >= len(scene["choices"])
    ):
        abort(400)

    chosen = scene["choices"][choice_index]
    next_scene_id = chosen["next"]

    #Update hidden personality score using values stored in narrative.json.
    # Not every choice defines a score, so only update if present.
    score_delta = chosen.get("score")
    if score_delta:
        update_scores(score_delta)

    return redirect(
        url_for(
            "narrative.show_scene",
            scene_id=next_scene_id
        )
    )

@narrative_bp.route("/results")
def results():
    """
    Display the personality profile, matched archetype, game
    recommendations, and LLM-generated character profile for the
    current session's completed assessment.

    The LLM only receives data already produced by the services below -
    it does not recalculate or influence any of it.
    """
    if not is_assessment_complete():
        return redirect(url_for("narrative.home"))

    scores = get_scores()
    profile = build_profile(scores)
    games = get_recommendations(scores)

    # Only the top 3 games, and only name/genres - matches what the
    # LLM service's public interface expects, and avoids passing the
    # full recommendation objects (score, website) it doesn't need.
    top_games = [
        {"name": game["name"], "genres": game["genres"]}
        for game in games[:3]
    ]

    character_profile = generate_character_profile(
        trait_data=profile["traits"],
        archetype_name=profile["archetype"],
        archetype_description=profile["description"],
        top_games=top_games,
    )

    return render_template(
        "results.html",
        profile=profile,
        games=games,
        character_profile=character_profile,
    )

@narrative_bp.route("/recommendations")
def recommendations():
    """
    Display the top recommended games for the current session's
    Big Five profile.
    """
    scores = get_scores()
    top_games = get_recommendations(scores)
    return render_template("recommendations.html", games=top_games)