"""Application configuration using pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All application settings loaded from environment / .env file."""

    # App
    app_name: str = "ComicCraft"
    debug: bool = True
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 10080  # 7 days

    # Database
    database_url: str = "sqlite:///./comiccraft.db"

    # Gemini AI
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-1.5-flash"
    gemini_image_model: str = "gemini-1.5-flash"

    # Image provider
    image_provider: str = "gemini"  # gemini | huggingface | mock
    hf_api_key: str = ""
    hf_image_model: str = "stabilityai/stable-diffusion-xl-base-1.0"

    # Demo mode
    demo_mode: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
