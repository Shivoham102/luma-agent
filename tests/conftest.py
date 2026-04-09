"""Shared fixtures for auth tests."""

import os
import sys

# Ensure the project root is on sys.path so ``import agent`` works.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables BEFORE importing any application modules so that
# agent/auth.py doesn't raise a RuntimeError for missing JWT_SECRET_KEY.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.database import Base, get_db

# Use an in-memory SQLite database for tests so they are fast and isolated.
TEST_DATABASE_URL = "sqlite:///./test_luma_agent.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop them afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """Return a FastAPI TestClient wired to the test database."""
    # Import here so load_dotenv / init_db in main don't interfere.
    from main import app

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client: TestClient):
    """Create a user via the signup endpoint and return the payload."""
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "password": "SecurePass1!",
        "linkedin_url": "https://linkedin.com/in/test",
        "job_title": "Engineer",
        "company": "TestCorp",
        "phone": "+1234567890",
        "twitter_x": "@testuser",
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    return {**payload, "response": resp.json()}


@pytest.fixture()
def auth_token(client: TestClient, registered_user: dict) -> str:
    """Login the registered user and return the JWT access token."""
    resp = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]
