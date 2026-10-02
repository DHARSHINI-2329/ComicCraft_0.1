"""Image generation provider abstraction.

Supports:
  - gemini   → Uses Gemini API (imagen model or flash with image output)
  - huggingface → Hugging Face Inference API
  - mock     → Returns a placeholder colored image (development only)
"""
import io
import logging
import hashlib
import httpx
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Base ──────────────────────────────────────────────────────────────────────

class ImageProvider:
    """Abstract image provider interface."""

    def generate(self, prompt: str, output_path: Path) -> bool:
        raise NotImplementedError

    def is_available(self) -> bool:
        return False


# ─── Mock Provider ─────────────────────────────────────────────────────────────

class MockImageProvider(ImageProvider):
    """Generates placeholder images for development/demo mode."""

    COLORS = [
        "#F4B942", "#E85D04", "#4A90D9", "#7CB342",
        "#9C27B0", "#00BCD4", "#FF7043", "#78909C",
    ]

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, output_path: Path) -> bool:
        try:
            # Use hash to pick a consistent color per prompt
            idx = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % len(self.COLORS)
            color = self.COLORS[idx]

            img = Image.new("RGB", (800, 600), color=color)
            draw = ImageDraw.Draw(img)

            # Dark overlay for text readability
            overlay = Image.new("RGBA", (800, 600), (0, 0, 0, 100))
            img.paste(Image.new("RGB", (800, 600), (30, 30, 30)), mask=overlay.split()[3])

            # Wrap and draw prompt text
            words = prompt[:200].split()
            lines, current = [], ""
            for word in words:
                if len(current) + len(word) + 1 <= 50:
                    current += (" " if current else "") + word
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            y = 250
            draw = ImageDraw.Draw(img)
            for line in lines[:6]:
                draw.text((400, y), line, fill="white", anchor="mm")
                y += 28

            draw.text((400, 560), "[DEMO MODE — No real image generated]",
                      fill="#F4B942", anchor="mm")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(output_path), "PNG")
            return True
        except Exception as e:
            logger.error(f"MockImageProvider error: {e}")
            return False


# ─── Hugging Face Provider ─────────────────────────────────────────────────────

class HuggingFaceImageProvider(ImageProvider):
    """Generates images via Hugging Face Inference API."""

    API_URL = "https://api-inference.huggingface.co/models/{model}"

    def __init__(self) -> None:
        self._api_key = settings.hf_api_key
        self._model = settings.hf_image_model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, output_path: Path) -> bool:
        if not self.is_available():
            logger.error("HuggingFace API key not configured")
            return False
        url = self.API_URL.format(model=self._model)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(response.content)
                return True
            else:
                logger.error(f"HuggingFace API error {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"HuggingFaceImageProvider exception: {e}")
            return False


# ─── Gemini Image Provider ─────────────────────────────────────────────────────

class GeminiImageProvider(ImageProvider):
    """Generates images via Gemini image generation API."""

    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_image_model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, output_path: Path) -> bool:
        if not self.is_available():
            logger.error("Gemini API key not configured for image generation")
            return False
        try:
            from google import genai
            from google.genai import types as gtypes
            client = genai.Client(api_key=self._api_key)

            # Use imagen-3.0-generate-001 for image generation
            try:
                result = client.models.generate_images(
                    model="imagen-3.0-generate-001",
                    prompt=prompt,
                    config=gtypes.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="4:3",
                    ),
                )
                if result.generated_images:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    img = result.generated_images[0].image
                    img.save(str(output_path))
                    return True
                logger.warning("Imagen returned no images — falling back to mock")
                return False
            except Exception as e:
                logger.warning(f"Imagen model failed ({e}), falling back to mock")
                return False

        except Exception as e:
            logger.error(f"GeminiImageProvider exception: {e}")
            return False


# ─── Factory ───────────────────────────────────────────────────────────────────

def get_image_provider() -> ImageProvider:
    """Return the configured image provider."""
    provider_name = settings.image_provider.lower()

    if settings.demo_mode:
        logger.info("DEMO MODE: using MockImageProvider")
        return MockImageProvider()

    if provider_name == "huggingface":
        p = HuggingFaceImageProvider()
        if p.is_available():
            return p
        logger.warning("HuggingFace API key missing — falling back to MockImageProvider")
        return MockImageProvider()

    if provider_name == "gemini":
        p = GeminiImageProvider()
        if p.is_available():
            return p
        logger.warning("Gemini API key missing — falling back to MockImageProvider")
        return MockImageProvider()

    if provider_name == "mock":
        return MockImageProvider()

    logger.warning(f"Unknown IMAGE_PROVIDER '{provider_name}' — using MockImageProvider")
    return MockImageProvider()
