"""Image generation provider abstraction.

Supports:
  - pollinations → Free, high-quality instant AI image generation (Flux / SDXL)
  - gemini       → Uses Gemini API (imagen model or fallback)
  - huggingface  → Hugging Face Inference API
  - mock         → Returns a stylized comic placeholder image (offline/dev fallback)
"""
import io
import logging
import hashlib
import urllib.parse
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
    """Generates styled comic placeholder images for offline fallback."""

    COLORS = [
        ("#1E1B4B", "#4338CA", "#A5B4FC"),  # Indigo comic theme
        ("#0F172A", "#0369A1", "#7DD3FC"),  # Sky blue comic theme
        ("#18181B", "#D97706", "#FDE68A"),  # Amber comic theme
        ("#1C1917", "#B91C1C", "#FCA5A5"),  # Crimson comic theme
        ("#064E3B", "#059669", "#6EE7B7"),  # Emerald comic theme
        ("#3B0764", "#7E22CE", "#D8B4FE"),  # Purple comic theme
    ]

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, output_path: Path) -> bool:
        try:
            # Pick a palette based on prompt hash
            idx = int(hashlib.md5(prompt.encode()).hexdigest(), 16) % len(self.COLORS)
            bg_dark, accent_color, text_color = self.COLORS[idx]

            width, height = 800, 600
            img = Image.new("RGB", (width, height), color=bg_dark)
            draw = ImageDraw.Draw(img)

            # Comic panel border
            draw.rectangle([12, 12, width - 12, height - 12], outline=accent_color, width=4)
            draw.rectangle([18, 18, width - 18, height - 18], outline="#ffffff", width=1)

            # Header badge
            draw.rectangle([width // 2 - 120, 24, width // 2 + 120, 56], fill=accent_color)
            draw.text((width // 2, 40), "COMIC PANEL", fill="white", anchor="mm")

            # Wrap and draw prompt text
            words = prompt[:260].split()
            lines, current = [], ""
            for word in words:
                if len(current) + len(word) + 1 <= 48:
                    current += (" " if current else "") + word
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

            y = 230 - (len(lines) * 14)
            for line in lines[:8]:
                draw.text((width // 2, y), line, fill=text_color, anchor="mm")
                y += 28

            # Bottom caption
            draw.text((width // 2, height - 40), "AI Story Illustration", fill="#94A3B8", anchor="mm")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(output_path), "PNG")
            logger.info(f"Generated placeholder comic image at {output_path}")
            return True
        except Exception as e:
            logger.error(f"MockImageProvider error: {e}")
            return False


# ─── Pollinations Free AI Provider ─────────────────────────────────────────────

class PollinationsImageProvider(ImageProvider):
    """Generates high-res AI comic images using Pollinations (Flux / SDXL)."""

    BASE_URL = "https://image.pollinations.ai/prompt/{prompt}"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, output_path: Path) -> bool:
        clean_prompt = prompt.replace("\n", " ").strip()
        encoded_prompt = urllib.parse.quote(clean_prompt)
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 100000

        # Try multiple URL variants
        candidate_urls = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&nologo=true&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}",
        ]

        # If prompt is long, also prepare a concise version
        if len(clean_prompt) > 200:
            short_encoded = urllib.parse.quote(clean_prompt[:200])
            candidate_urls.append(f"https://image.pollinations.ai/prompt/{short_encoded}?width=800&height=600&nologo=true&seed={seed}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }

        for url in candidate_urls:
            try:
                logger.info("Requesting AI image from Pollinations...")
                with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
                    response = client.get(url)

                if response.status_code == 200 and len(response.content) > 1000:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    logger.info(f"Pollinations image generated successfully: {output_path}")
                    return True
                elif response.status_code in (402, 403):
                    logger.warning(f"Pollinations returned {response.status_code} (requires payment/auth), switching directly to fallback")
                    break
                else:
                    logger.warning(f"Pollinations url {url[:70]} returned status {response.status_code}")
            except Exception as e:
                logger.warning(f"Pollinations attempt failed ({e})")

        # Graceful fallback to Mock image if Pollinations is blocked / offline
        logger.info("Pollinations unavailable, falling back to styled comic mock generator...")
        return MockImageProvider().generate(prompt, output_path)


# ─── Hugging Face Provider ─────────────────────────────────────────────────────

class HuggingFaceImageProvider(ImageProvider):
    """Generates images via Hugging Face Inference API."""

    def __init__(self) -> None:
        self._api_key = settings.hf_api_key
        self._model = settings.hf_image_model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, output_path: Path) -> bool:
        if not self.is_available():
            logger.error("HuggingFace API key not configured")
            return False

        urls = [
            f"https://router.huggingface.co/hf-inference/models/{self._model}",
            f"https://api-inference.huggingface.co/models/{self._model}",
        ]
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
            },
        }

        for url in urls:
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200 and len(response.content) > 500:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    return True
                else:
                    logger.warning(f"HF url {url} returned {response.status_code}: {response.text[:150]}")
            except Exception as e:
                logger.warning(f"HF request to {url} failed: {e}")

        # Fallback to Pollinations then Mock
        logger.info("Falling back to Pollinations provider...")
        return PollinationsImageProvider().generate(prompt, output_path) or MockImageProvider().generate(prompt, output_path)


# ─── Gemini Image Provider ─────────────────────────────────────────────────────

class GeminiImageProvider(ImageProvider):
    """Generates images via Gemini API with automatic fallback to Pollinations and Mock."""

    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_image_model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, output_path: Path) -> bool:
        if self.is_available():
            try:
                from google import genai
                from google.genai import types as gtypes
                client = genai.Client(api_key=self._api_key)

                # Attempt Imagen if enabled in enterprise project
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
                        img_bytes = result.generated_images[0].image.image_bytes
                        output_path.write_bytes(img_bytes)
                        return True
                except Exception as e:
                    logger.info(f"Gemini Imagen not enabled for this key ({e}); switching to Pollinations AI generator.")
            except Exception as e:
                logger.info(f"Gemini client image attempt: {e}")

        # High quality automatic fallback to Pollinations AI
        pol_success = PollinationsImageProvider().generate(prompt, output_path)
        if pol_success:
            return True

        # Offline fallback
        return MockImageProvider().generate(prompt, output_path)


# ─── Factory ───────────────────────────────────────────────────────────────────

def get_image_provider() -> ImageProvider:
    """Return the configured image provider with resilient fallback."""
    provider_name = settings.image_provider.lower()

    if settings.demo_mode:
        logger.info("DEMO MODE: using MockImageProvider")
        return MockImageProvider()

    if provider_name == "pollinations":
        return PollinationsImageProvider()

    if provider_name == "huggingface":
        p = HuggingFaceImageProvider()
        if p.is_available():
            return p
        return PollinationsImageProvider()

    if provider_name == "gemini":
        return GeminiImageProvider()

    if provider_name == "mock":
        return MockImageProvider()

    # Default resilient provider
    return GeminiImageProvider()
