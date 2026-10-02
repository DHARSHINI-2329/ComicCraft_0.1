"""Gemini AI provider for text generation (google-genai SDK)."""
import json
import logging
import re
from typing import Optional
from google import genai
from google.genai import types
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiProvider:
    """Wraps the Google Gemini API for text generation."""

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY is not set — AI text generation will fail.")
            self._configured = False
            self._client = None
        else:
            self._client = genai.Client(api_key=settings.gemini_api_key)
            self._configured = True
        self._text_model_name = settings.gemini_text_model

    def is_available(self) -> bool:
        return self._configured

    def generate_text(self, prompt: str, temperature: float = 0.7) -> str:
        """Send a prompt and return the response text, with candidate model fallback."""
        if not self._configured or not self._client:
            raise RuntimeError(
                "Gemini API key is not configured. "
                "Set GEMINI_API_KEY in your .env file."
            )
        candidate_models = [
            self._text_model_name,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite-preview",
            "gemini-flash-latest",
        ]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))
        last_exc = None

        for model in candidate_models:
            try:
                response = self._client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=8192,
                    ),
                )
                return response.text
            except Exception as e:
                logger.warning(f"Gemini generate_content failed on model '{model}': {e}")
                last_exc = e

        raise last_exc or RuntimeError("Failed to generate content with available Gemini models")

    def generate_json(self, prompt: str, retries: int = 2) -> dict:
        """Generate text and parse as JSON with retry logic."""
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                raw = self.generate_text(prompt, temperature=0.6 + attempt * 0.05)
                return self._parse_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"JSON parse attempt {attempt + 1} failed: {e}")
                last_error = e
        raise ValueError(f"Failed to parse valid JSON after {retries + 1} attempts: {last_error}")

    def _parse_json(self, text: str) -> dict:
        """Extract and parse JSON from model output."""
        text = text.strip()
        # Remove markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        text = text.strip()
        # Find first { ... } block
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in response")
        # Find matching closing brace
        depth = 0
        end = -1
        for i, ch in enumerate(text[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end == -1:
            raise ValueError("Unmatched braces in JSON response")
        return json.loads(text[start:end])
