"""Character service: manages character profiles for visual consistency."""
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.character import Character
from app.utils.file_utils import new_id

logger = logging.getLogger(__name__)


class CharacterService:
    """Creates and retrieves character profiles."""

    def create_from_profile(
        self,
        db: Session,
        comic_id: str,
        profile: dict,
    ) -> Character:
        """Persist a character profile to the database."""
        visual_ids = profile.get("visual_identifiers", [])
        if isinstance(visual_ids, list):
            visual_ids_json = json.dumps(visual_ids)
        else:
            visual_ids_json = json.dumps([str(visual_ids)])

        char = Character(
            comic_id=comic_id,
            name=str(profile.get("name", "")),
            species=str(profile.get("species", "")),
            age=str(profile.get("age", "")),
            appearance=str(profile.get("appearance", "")),
            clothing=str(profile.get("clothing", "")),
            personality=str(profile.get("personality", "")),
            visual_identifiers=visual_ids_json,
        )
        db.add(char)
        db.commit()
        db.refresh(char)
        logger.info(f"Character profile created for '{char.name}' (comic {comic_id})")
        return char

    def get_profile_dict(self, character: Optional[Character]) -> dict:
        """Convert a Character model to a plain dict for prompt building."""
        if not character:
            return {}
        visual_ids = []
        if character.visual_identifiers:
            try:
                visual_ids = json.loads(character.visual_identifiers)
            except json.JSONDecodeError:
                visual_ids = [character.visual_identifiers]
        return {
            "name": character.name,
            "species": character.species or "",
            "age": character.age or "",
            "appearance": character.appearance or "",
            "clothing": character.clothing or "",
            "personality": character.personality or "",
            "visual_identifiers": visual_ids,
        }
