"""Story service: generates structured comic outlines via Gemini."""
import json
import logging
from typing import Optional
from app.ai.gemini_provider import GeminiProvider
from app.ai.prompts import build_outline_prompt, build_continuation_prompt, build_panel_regeneration_prompt
from app.schemas.panel import PanelOutline, DialogueLine
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Demo data ────────────────────────────────────────────────────────────────

DEMO_OUTLINE = {
    "title": "Luna and the Glowing Door",
    "summary": "A brave fox named Luna discovers a mysterious glowing door in an enchanted forest and must choose whether to open it.",
    "character_profile": {
        "name": "Luna",
        "species": "Fox",
        "age": "Young adult",
        "appearance": "Sleek orange fox with white chest fur and emerald green eyes",
        "clothing": "Blue woolen scarf wrapped around neck",
        "personality": "Brave, curious, and determined",
        "visual_identifiers": ["orange fur", "blue scarf", "emerald green eyes", "white chest patch"],
    },
    "panels": [
        {
            "panel_number": 1,
            "title": "Into the Enchanted Forest",
            "scene_description": "Luna trots through a misty, moonlit forest. Ancient trees tower around her.",
            "narration": "Deep in the Enchanted Forest, where fireflies danced like stars...",
            "dialogue": [{"character": "Luna", "text": "Something feels different tonight."}],
            "image_prompt": "A young orange fox with a blue scarf walks through a moonlit enchanted forest, fireflies glowing around ancient trees, comic book art style, dramatic lighting, wide shot",
        },
        {
            "panel_number": 2,
            "title": "The Discovery",
            "scene_description": "Luna stops, her eyes wide. Between two ancient oaks stands a door radiating golden light.",
            "narration": "Then she saw it — a door that had no business being there.",
            "dialogue": [{"character": "Luna", "text": "A door? Out here?"}],
            "image_prompt": "An orange fox with blue scarf stands before a glowing golden magical door between two huge oak trees in an enchanted forest, sense of wonder, comic book art style, golden light rays",
        },
        {
            "panel_number": 3,
            "title": "The Warning",
            "scene_description": "A wise old owl perches above the door, blocking the way.",
            "narration": "A guardian had been waiting.",
            "dialogue": [
                {"character": "Owl", "text": "Those who enter must solve the forest's oldest riddle."},
                {"character": "Luna", "text": "Then I'll solve it."},
            ],
            "image_prompt": "An orange fox with blue scarf confronts a wise old owl perched above a glowing door in an enchanted forest, tense moment, comic book art style, dramatic lighting",
        },
        {
            "panel_number": 4,
            "title": "The Answer",
            "scene_description": "Luna closes her eyes, concentrating. The answer comes from within.",
            "narration": "The riddle asked what was stronger than magic. Luna already knew.",
            "dialogue": [{"character": "Luna", "text": "Courage. The answer is courage."}],
            "image_prompt": "An orange fox with blue scarf concentrating with eyes closed, glowing runes floating around, magical forest setting, comic book art style, warm golden light",
        },
        {
            "panel_number": 5,
            "title": "Beyond the Door",
            "scene_description": "The door swings open, revealing a beautiful hidden world filled with light.",
            "narration": "And just like that, the Enchanted Forest revealed its greatest secret.",
            "dialogue": [{"character": "Luna", "text": "I knew there was something more out there."}],
            "image_prompt": "An orange fox with blue scarf stepping through a glowing magical doorway into a beautiful luminous realm beyond, triumphant moment, comic book art style, epic wide shot",
        },
    ],
}


def _validate_panels(raw_panels: list) -> list[PanelOutline]:
    """Validate and parse panel data from AI output."""
    panels = []
    for raw in raw_panels:
        dialogue = [
            DialogueLine(character=d.get("character", ""), text=d.get("text", ""))
            for d in raw.get("dialogue", [])
            if isinstance(d, dict)
        ]
        panel = PanelOutline(
            panel_number=int(raw.get("panel_number", len(panels) + 1)),
            title=str(raw.get("title", f"Panel {len(panels) + 1}")),
            scene_description=str(raw.get("scene_description", "")),
            narration=str(raw.get("narration", "")),
            dialogue=dialogue,
            image_prompt=str(raw.get("image_prompt", "")),
        )
        panels.append(panel)
    return sorted(panels, key=lambda p: p.panel_number)


class StoryService:
    """Handles AI-powered story generation."""

    def __init__(self) -> None:
        self._gemini = GeminiProvider()

    def generate_outline(
        self,
        story_prompt: str,
        character_name: str,
        setting: str,
        tone: str,
        art_style: str,
        character_description: Optional[str] = None,
    ) -> dict:
        """Generate a full 5-panel comic outline.

        Returns a dict with keys: title, summary, character_profile, panels.
        """
        if settings.demo_mode:
            logger.info("DEMO MODE: returning demo outline")
            return DEMO_OUTLINE

        if not self._gemini.is_available():
            raise RuntimeError(
                "Gemini API key is not configured. "
                "Please set GEMINI_API_KEY in your .env file, "
                "or set DEMO_MODE=true to use the demo story."
            )

        prompt = build_outline_prompt(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style,
            character_description=character_description,
        )

        logger.info(f"Generating comic outline for '{character_name}' in {setting}")
        data = self._gemini.generate_json(prompt)

        # Validate panels
        raw_panels = data.get("panels", [])
        if len(raw_panels) != 5:
            logger.warning(f"AI returned {len(raw_panels)} panels, expected 5")
            if len(raw_panels) < 5:
                raise ValueError(f"AI returned only {len(raw_panels)} panels. Expected exactly 5.")

        panels = _validate_panels(raw_panels[:5])
        data["panels"] = [p.model_dump() for p in panels]
        return data

    def generate_continuation(
        self,
        previous_title: str,
        previous_summary: str,
        character_profile: dict,
        setting: str,
        tone: str,
        art_style: str,
        chapter_number: int,
        previous_panels_summary: str,
    ) -> dict:
        """Generate a continuation chapter outline."""
        if settings.demo_mode:
            demo = dict(DEMO_OUTLINE)
            demo["title"] = f"Chapter {chapter_number}: {previous_title} Continues"
            demo["summary"] = f"The adventure continues for {character_profile.get('name', 'our hero')}."
            return demo

        if not self._gemini.is_available():
            raise RuntimeError("Gemini API key is not configured.")

        prompt = build_continuation_prompt(
            previous_title=previous_title,
            previous_summary=previous_summary,
            character_profile=character_profile,
            setting=setting,
            tone=tone,
            art_style=art_style,
            chapter_number=chapter_number,
            previous_panels_summary=previous_panels_summary,
        )

        logger.info(f"Generating chapter {chapter_number} continuation")
        data = self._gemini.generate_json(prompt)

        raw_panels = data.get("panels", [])
        panels = _validate_panels(raw_panels[:5])
        data["panels"] = [p.model_dump() for p in panels]
        return data

    def regenerate_panel(
        self,
        comic_title: str,
        panel_number: int,
        character_profile: dict,
        story_summary: str,
        original_scene_description: str,
        setting: str,
        tone: str,
        art_style: str,
    ) -> dict:
        """Regenerate a single panel's content."""
        if settings.demo_mode:
            panel_idx = panel_number - 1
            if 0 <= panel_idx < len(DEMO_OUTLINE["panels"]):
                return DEMO_OUTLINE["panels"][panel_idx]
            return DEMO_OUTLINE["panels"][0]

        if not self._gemini.is_available():
            raise RuntimeError("Gemini API key is not configured.")

        prompt = build_panel_regeneration_prompt(
            comic_title=comic_title,
            panel_number=panel_number,
            character_profile=character_profile,
            story_summary=story_summary,
            original_scene_description=original_scene_description,
            setting=setting,
            tone=tone,
            art_style=art_style,
        )

        logger.info(f"Regenerating panel {panel_number}")
        data = self._gemini.generate_json(prompt)
        return data
