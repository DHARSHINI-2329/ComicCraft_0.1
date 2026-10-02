"""Tests for ComicCraft application."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.database import Base, get_db

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test."""
    from app.models import user, comic, panel, character, generation_job  # noqa
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_client(client):
    """Client with a registered and logged-in user."""
    # Register
    r = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
    })
    assert r.status_code == 200, r.text
    # Login
    r = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass123",
    })
    assert r.status_code == 200
    token = r.json()["access_token"]
    client.cookies.set("access_token", token)
    return client, token


# ── Health ────────────────────────────────────────────────────────

def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "app" in data


# ── Auth ──────────────────────────────────────────────────────────

def test_register_success(client):
    r = client.post("/auth/register", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
    })
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_register_duplicate_username(client):
    data = {"username": "dup", "email": "dup@example.com", "password": "pass1234"}
    client.post("/auth/register", json=data)
    r = client.post("/auth/register", json={**data, "email": "other@example.com"})
    assert r.status_code == 400


def test_register_duplicate_email(client):
    data = {"username": "user1", "email": "same@example.com", "password": "pass1234"}
    client.post("/auth/register", json=data)
    r = client.post("/auth/register", json={**data, "username": "user2"})
    assert r.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={
        "username": "loginuser", "email": "lg@e.com", "password": "pass1234"
    })
    r = client.post("/auth/login", json={"username": "loginuser", "password": "pass1234"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "username": "badpw", "email": "bp@e.com", "password": "correct123"
    })
    r = client.post("/auth/login", json={"username": "badpw", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"username": "nobody", "password": "nope"})
    assert r.status_code == 401


# ── Comic generation (requires auth) ─────────────────────────────

def test_generate_comic_unauthenticated(client):
    r = client.post("/api/generate-comic/json", json={
        "story_prompt": "A fox discovers a door",
        "character_name": "Luna",
        "setting": "Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    assert r.status_code == 401


def test_generate_comic_authenticated(auth_client):
    """This test checks the API endpoint logic, not full AI generation."""
    import os
    os.environ["DEMO_MODE"] = "true"
    client, _ = auth_client
    r = client.post("/api/generate-comic/json", json={
        "story_prompt": "A brave fox discovers a mysterious glowing door",
        "character_name": "Luna",
        "setting": "Enchanted Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    # Even if generation fails (no API key in test), the job should be created
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "comic_id" in data
    assert "job_id" in data


def test_generate_comic_invalid_prompt(auth_client):
    client, _ = auth_client
    r = client.post("/api/generate-comic/json", json={
        "story_prompt": "short",  # too short
        "character_name": "Luna",
        "setting": "Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    assert r.status_code == 422  # Pydantic validation error


# ── Comic ownership ───────────────────────────────────────────────

def test_comic_ownership_403(auth_client, client):
    """User B cannot access User A's comic."""
    import os
    os.environ["DEMO_MODE"] = "true"
    client_a, _ = auth_client

    # Create comic as user A
    r = client_a.post("/api/generate-comic/json", json={
        "story_prompt": "A fox discovers a glowing door in the forest",
        "character_name": "Luna",
        "setting": "Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    comic_id = r.json()["comic_id"]

    # Register and login as user B
    client.post("/auth/register", json={
        "username": "userb", "email": "b@b.com", "password": "pass1234"
    })
    rb = client.post("/auth/login", json={"username": "userb", "password": "pass1234"})
    token_b = rb.json()["access_token"]
    client.cookies.set("access_token", token_b)

    # Try to access user A's comic
    r2 = client.get(f"/api/comics/{comic_id}")
    assert r2.status_code == 404  # Not found (not their comic)


# ── Favorite ──────────────────────────────────────────────────────

def test_toggle_favorite(auth_client):
    import os
    os.environ["DEMO_MODE"] = "true"
    client, _ = auth_client

    r = client.post("/api/generate-comic/json", json={
        "story_prompt": "A fox discovers a glowing door deep in the woods",
        "character_name": "Luna",
        "setting": "Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    comic_id = r.json()["comic_id"]

    # Toggle favorite on
    r2 = client.post(f"/api/comics/{comic_id}/favorite")
    assert r2.status_code == 200
    assert r2.json()["is_favorite"] is True

    # Toggle favorite off
    r3 = client.post(f"/api/comics/{comic_id}/favorite")
    assert r3.status_code == 200
    assert r3.json()["is_favorite"] is False


# ── Delete ────────────────────────────────────────────────────────

def test_delete_comic(auth_client):
    import os
    os.environ["DEMO_MODE"] = "true"
    client, _ = auth_client

    r = client.post("/api/generate-comic/json", json={
        "story_prompt": "A fox finds a mysterious glowing artifact",
        "character_name": "Luna",
        "setting": "Forest",
        "tone": "Adventure",
        "art_style": "Comic Book",
    })
    comic_id = r.json()["comic_id"]

    rd = client.delete(f"/api/comics/{comic_id}")
    assert rd.status_code == 200

    # Should now be 404
    r2 = client.get(f"/api/comics/{comic_id}")
    assert r2.status_code == 404


# ── Input validation ──────────────────────────────────────────────

def test_register_short_username(client):
    r = client.post("/auth/register", json={
        "username": "ab",
        "email": "ab@e.com",
        "password": "pass1234",
    })
    assert r.status_code == 422


def test_register_weak_password(client):
    r = client.post("/auth/register", json={
        "username": "validuser",
        "email": "valid@e.com",
        "password": "short",
    })
    assert r.status_code == 422


# ── Web pages ─────────────────────────────────────────────────────

def test_homepage(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"ComicCraft" in r.content


def test_about_page(client):
    r = client.get("/about")
    assert r.status_code == 200


def test_login_page(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_register_page(client):
    r = client.get("/register")
    assert r.status_code == 200


def test_create_page_requires_auth(client):
    r = client.get("/create", follow_redirects=False)
    assert r.status_code == 302  # redirect to login


def test_library_requires_auth(client):
    r = client.get("/library", follow_redirects=False)
    assert r.status_code == 302


# ── AI schemas ────────────────────────────────────────────────────

def test_panel_outline_validation():
    from app.schemas.panel import PanelOutline, DialogueLine
    p = PanelOutline(
        panel_number=1,
        title="Test Panel",
        scene_description="A scene",
        narration="Some narration",
        dialogue=[DialogueLine(character="Luna", text="Hello!")],
        image_prompt="An orange fox in a forest",
    )
    assert p.panel_number == 1
    assert len(p.dialogue) == 1
    assert p.dialogue[0].character == "Luna"


def test_comic_create_request_validation():
    from app.schemas.comic import ComicCreateRequest
    from pydantic import ValidationError

    # Valid
    r = ComicCreateRequest(
        story_prompt="A brave fox discovers a mysterious door in the forest",
        character_name="Luna",
        setting="Forest",
        tone="Adventure",
        art_style="Comic Book",
    )
    assert r.character_name == "Luna"

    # Invalid: short prompt
    with pytest.raises(ValidationError):
        ComicCreateRequest(
            story_prompt="hi",
            character_name="Luna",
            setting="Forest",
            tone="Adventure",
            art_style="Comic Book",
        )
