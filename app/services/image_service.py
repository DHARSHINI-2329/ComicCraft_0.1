"""Image service: generates and stores panel images."""
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.ai.image_provider import get_image_provider
from app.ai.prompts import build_image_prompt
from app.models.panel import Panel
from app.utils.file_utils import panel_image_path

logger = logging.getLogger(__name__)


class ImageService:
    """Handles image generation for comic panels."""

    def generate_panel_image(
        self,
        db: Session,
        panel: Panel,
        character_profile: dict,
        art_style: str,
    ) -> bool:
        """Generate an image for a single panel and update its DB record.

        Returns True on success, False on failure. Never raises.
        """
        try:
            provider = get_image_provider()
            logger.info(
                f"Generating image for panel {panel.panel_number} "
                f"(comic {panel.comic_id}) using {type(provider).__name__}"
            )

            enhanced_prompt = build_image_prompt(
                base_prompt=panel.image_prompt,
                character_profile=character_profile,
                art_style=art_style,
                panel_number=panel.panel_number,
            )

            output_path = panel_image_path(panel.comic_id, panel.panel_number)
            success = provider.generate(enhanced_prompt, output_path)

            if success:
                panel.image_path = str(output_path)
                panel.generation_status = "COMPLETED"
                logger.info(f"Panel {panel.panel_number} image saved to {output_path}")
            else:
                panel.generation_status = "FAILED"
                logger.error(f"Image generation failed for panel {panel.panel_number}")

            db.commit()
            return success

        except Exception as e:
            logger.exception(f"Unexpected error generating panel {panel.panel_number}: {e}")
            panel.generation_status = "FAILED"
            db.commit()
            return False

    def generate_all_panel_images(
        self,
        db: Session,
        panels: list[Panel],
        character_profile: dict,
        art_style: str,
    ) -> dict[int, bool]:
        """Generate images for all panels. Returns {panel_number: success}."""
        results = {}
        for panel in panels:
            results[panel.panel_number] = self.generate_panel_image(
                db=db,
                panel=panel,
                character_profile=character_profile,
                art_style=art_style,
            )
        return results
