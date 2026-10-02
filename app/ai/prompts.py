"""Reusable AI prompt builder functions.

All prompts are centralized here so they can be tuned independently
of route handlers and service logic.
"""
from typing import Optional


# ─── Story / Outline Prompts ──────────────────────────────────────────────────

def build_outline_prompt(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
    character_description: Optional[str] = None,
) -> str:
    """Build the Gemini prompt that returns a structured 5-panel comic outline."""
    char_desc_section = (
        f"Character Description (provided by user): {character_description}"
        if character_description
        else "No specific character description provided — infer appearance from the story context."
    )

    return f"""You are a professional comic story writer. Create a complete 5-panel comic outline.

STORY IDEA: {story_prompt}
MAIN CHARACTER: {character_name}
{char_desc_section}
SETTING: {setting}
TONE: {tone}
ART STYLE: {art_style}

REQUIREMENTS:
- Produce EXACTLY 5 panels
- Each panel must advance the story
- Create a coherent narrative arc: Setup → Discovery → Conflict → Climax → Resolution
- Give the character consistent visual traits
- Dialogue must be concise and natural
- Image prompts must be detailed and suitable for image generation
- Do NOT include text, watermarks, or logos in image prompts
- Do NOT add random background characters that conflict with the story

Return ONLY valid JSON (no markdown, no code fences) in this exact structure:
{{
  "title": "Story title here",
  "summary": "2-3 sentence story summary",
  "character_profile": {{
    "name": "{character_name}",
    "species": "species or human",
    "age": "approximate age or range",
    "appearance": "detailed physical appearance",
    "clothing": "specific clothing description",
    "personality": "personality traits",
    "visual_identifiers": ["identifier 1", "identifier 2", "identifier 3"]
  }},
  "panels": [
    {{
      "panel_number": 1,
      "title": "Panel title",
      "scene_description": "What is happening in this scene",
      "narration": "Caption/narration text for this panel",
      "dialogue": [
        {{"character": "{character_name}", "text": "Dialogue text"}}
      ],
      "image_prompt": "Detailed image generation prompt including character appearance, action, setting, lighting, composition, {art_style} art style"
    }}
  ]
}}"""


def build_continuation_prompt(
    previous_title: str,
    previous_summary: str,
    character_profile: dict,
    setting: str,
    tone: str,
    art_style: str,
    chapter_number: int,
    previous_panels_summary: str,
) -> str:
    """Build the prompt for continuing a story into the next chapter."""
    char = character_profile
    return f"""You are a professional comic story writer continuing an existing story.

ORIGINAL TITLE: {previous_title}
CHAPTER {chapter_number - 1} SUMMARY: {previous_summary}
EVENTS SO FAR: {previous_panels_summary}

MAIN CHARACTER: {char.get("name")}
CHARACTER APPEARANCE: {char.get("appearance")}
CHARACTER CLOTHING: {char.get("clothing")}
VISUAL IDENTIFIERS: {", ".join(char.get("visual_identifiers", []))}
SETTING: {setting}
TONE: {tone}
ART STYLE: {art_style}

REQUIREMENTS:
- This is Chapter {chapter_number} — continue DIRECTLY from where Chapter {chapter_number - 1} ended
- Do NOT restart the story
- Maintain the same character appearance exactly
- Keep the same setting/world unless the story naturally moves
- Produce EXACTLY 5 panels
- Maintain narrative continuity

Return ONLY valid JSON (no markdown, no code fences) in this exact structure:
{{
  "title": "Chapter {chapter_number}: Subtitle here",
  "summary": "Summary of this chapter",
  "character_profile": {{
    "name": "{char.get("name")}",
    "species": "{char.get("species", "unknown")}",
    "age": "{char.get("age", "unknown")}",
    "appearance": "{char.get("appearance", "")}",
    "clothing": "{char.get("clothing", "")}",
    "personality": "{char.get("personality", "")}",
    "visual_identifiers": {char.get("visual_identifiers", [])}
  }},
  "panels": [
    {{
      "panel_number": 1,
      "title": "Panel title",
      "scene_description": "Scene description",
      "narration": "Narration text",
      "dialogue": [{{"character": "name", "text": "dialogue"}}],
      "image_prompt": "Detailed image prompt with character appearance, {art_style} art style"
    }}
  ]
}}"""


def build_panel_regeneration_prompt(
    comic_title: str,
    panel_number: int,
    character_profile: dict,
    story_summary: str,
    original_scene_description: str,
    setting: str,
    tone: str,
    art_style: str,
) -> str:
    """Build prompt for regenerating a single panel."""
    char = character_profile
    return f"""You are a professional comic story writer regenerating a single panel.

COMIC TITLE: {comic_title}
STORY SUMMARY: {story_summary}
PANEL NUMBER: {panel_number} of 5

CHARACTER: {char.get("name")}
APPEARANCE: {char.get("appearance")}
CLOTHING: {char.get("clothing")}
VISUAL IDENTIFIERS: {", ".join(char.get("visual_identifiers", []))}
SETTING: {setting}
TONE: {tone}
ART STYLE: {art_style}

ORIGINAL SCENE: {original_scene_description}

Regenerate ONLY this panel with fresh narration, dialogue, and a new image prompt.
Keep the character appearance IDENTICAL.
Keep the scene context consistent with the overall story.

Return ONLY valid JSON (no markdown, no code fences):
{{
  "panel_number": {panel_number},
  "title": "Panel title",
  "scene_description": "Scene description",
  "narration": "Narration text",
  "dialogue": [{{"character": "name", "text": "dialogue"}}],
  "image_prompt": "Detailed image prompt with character appearance, {art_style} art style"
}}"""


def build_image_prompt(
    base_prompt: str,
    character_profile: dict,
    art_style: str,
    panel_number: int,
) -> str:
    """Enhance a raw image prompt with character consistency markers."""
    char = character_profile
    identifiers = ", ".join(char.get("visual_identifiers", []))
    return (
        f"{base_prompt}. "
        f"CHARACTER CONSISTENCY: {char.get('name')} has {char.get('appearance', '')}. "
        f"Wearing {char.get('clothing', '')}. "
        f"Visual identifiers: {identifiers}. "
        f"ART STYLE: {art_style}. "
        f"High quality, detailed, no text, no watermarks, no logos. "
        f"Comic panel {panel_number} of 5."
    )
