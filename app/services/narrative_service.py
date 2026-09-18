"""
Narrative service.

Responsible for loading scene data from JSON and providing
a simple interface for retrieving narrative scenes.
Routes call into this service rather than reading
the JSON file directly.
"""

import json
import os

from flask import session

# Path to the narrative data file, resolved relative to this file's location
# so it works regardless of the working directory the app is run from.
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "narrative.json")

_narrative_data = None  # simple in-memory cache, loaded once


def _load_data():
    """Load narrative.json into memory the first time it's needed."""
    global _narrative_data
    if _narrative_data is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _narrative_data = json.load(f)
    return _narrative_data


def get_start_scene_id():
    """Return the ID of the first scene, as defined in narrative.json."""
    return _load_data()["start_scene"]


def get_scene(scene_id):
    """
    Return the scene dict for a given scene_id, or None if it doesn't exist.

    Returning None (rather than raising) lets the route decide how to handle
    a missing/invalid scene ID, e.g. with a 404.
    """
    return _load_data()["scenes"].get(scene_id)


def mark_assessment_complete():
    """Mark the current narrative assessment as completed."""
    session["assessment_complete"] = True


def mark_assessment_incomplete():
    """Mark the current narrative assessment as incomplete."""
    session["assessment_complete"] = False


def is_assessment_complete():
    """Return whether the current assessment has been completed."""
    return session.get("assessment_complete", False)