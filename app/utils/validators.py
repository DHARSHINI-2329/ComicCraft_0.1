"""Input validation helpers."""
import re
from typing import Optional


def sanitize_text(text: str, max_length: int = 2000) -> str:
    """Strip and truncate text."""
    return text.strip()[:max_length]


def is_valid_username(username: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_]{3,50}$", username))


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
