"""
LLM personalisation service.

Generates a short personalised RPG character profile from
already-calculated assessment results.

This service does not calculate or modify personality scores,
archetypes, or game recommendations.

The public function always returns a dict with an "available" key,
so callers never need to guess whether generation succeeded:

    {
        "available": True,
        "character_name": "...",
        "backstory": "...",
        "play_style": "...",
        "strengths": "...",
        "challenges": "...",
        "game_fit": "...",
    }

On any failure (missing key, API error, malformed/incomplete/invalid
JSON), "available" is False and the six content fields are empty
strings - the caller/template is expected to show one fallback message
in that case, not six separate ones.
"""

import json

from openai import OpenAI
from flask import current_app

_MODEL = "gpt-4o-mini"

_FALLBACK_MESSAGE = "Personalised character generation is currently unavailable."

# The six fields the LLM must return. Used both to build the prompt's
# instructions and to validate the parsed JSON actually contains them.
_REQUIRED_FIELDS = [
    "character_name",
    "backstory",
    "play_style",
    "strengths",
    "challenges",
    "game_fit",
]


def _empty_result():
    """
    Build the fallback shape: available=False, all content fields empty.
    Used whenever generation fails for any reason.
    """
    result = {"available": False}
    result.update({field: "" for field in _REQUIRED_FIELDS})
    return result


def _build_prompt(trait_data, archetype_name, archetype_description, top_games):
    """
    Build the prompt sent to the LLM from existing assessment results.

    Asks for a JSON object with exactly the six required fields, so the
    response can be parsed into a structured character profile instead
    of one paragraph of free text.
    """

    trait_lines = "\n".join(
        f"- {trait.capitalize()}: {data['level']} ({data['score']:+d})"
        for trait, data in trait_data.items()
    )

    if top_games:
        game_lines = "\n".join(
            f"- {game['name']} ({', '.join(game['genres'])})"
            for game in top_games
        )
    else:
        game_lines = "- (no strong game matches for this profile)"

    prompt = f"""
Based on the following assessment results, write a short personalised
RPG character profile.

Archetype: {archetype_name}
Archetype description: {archetype_description}

Big Five personality traits:
{trait_lines}

Recommended games for context:
{game_lines}

Respond with ONLY a JSON object (no other text before or after it)
containing exactly these six fields, all as plain strings:

- character_name: a short character name
- backstory: a short character description/backstory (2-3 sentences)
- play_style: a brief description of how this character plays (1-2 sentences)
- strengths: one short natural sentence describing personality strengths
- challenges: one short natural sentence describing character challenges
- game_fit: one short sentence explaining why the recommended games
  suit this profile

Do not use Markdown formatting (no asterisks, dashes, or headers) and
do not use HTML tags - plain sentences only.
Do not mention "Big Five", "personality assessment", or present this
as a scientific or diagnostic result.
Do not invent different trait scores or a different archetype than the
ones given above.
""".strip()

    return prompt


def generate_character_profile(
    trait_data,
    archetype_name,
    archetype_description,
    top_games=None,
):
    """
    Generate a personalised RPG character profile.

    Always returns a dict with "available" plus the six content fields
    (see module docstring). Callers/templates check "available" once
    rather than handling failure per-field.
    """
    top_games = top_games or []

    api_key = current_app.config.get("OPENAI_API_KEY")

    if not api_key:
        return _empty_result()

    prompt = _build_prompt(
        trait_data,
        archetype_name,
        archetype_description,
        top_games,
    )

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model=_MODEL,
            input=prompt,
        )

        parsed = json.loads(response.output_text.strip())

        # Validate the parsed response strictly before trusting it:
        # - must be a JSON object (dict), not a list/string/number
        # - must contain exactly the six required fields, no more, no less
        # - every field's value must be a string
        # Any failure here means the LLM didn't follow the requested
        # format closely enough to trust, so fall back safely.
        if not isinstance(parsed, dict):
            return _empty_result()

        if set(parsed.keys()) != set(_REQUIRED_FIELDS):
            return _empty_result()

        if not all(isinstance(parsed[field], str) for field in _REQUIRED_FIELDS):
            return _empty_result()

        result = {"available": True}
        result.update({field: parsed[field] for field in _REQUIRED_FIELDS})
        return result

    except Exception:
        # Covers API errors, network failures, and json.loads() failing
        # on a malformed response - all degrade to the same safe fallback.
        return _empty_result()