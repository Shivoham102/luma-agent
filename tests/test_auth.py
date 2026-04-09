"""Tests for authentication endpoints: signup, login, /auth/me, and /token protection."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt

from agent.auth import JWT_ALGORITHM, JWT_SECRET_KEY

# ---------------------------------------------------------------------------
# Signup tests
# ---------------------------------------------------------------------------


def test_signup_success(client: TestClient):
    """POST /auth/signup creates a user and returns profile without passwords."""
    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "StrongP@ss1",
        "linkedin_url": "https://linkedin.com/in/alice",
        "job_title": "Dev",
        "company": "Acme",
        "phone": "+1111111111",
        "twitter_x": "@alice",
        "luma_email": "alice_luma@example.com",
        "luma_password": "LumaSecret123",
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    # Should contain user fields
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert data["linkedin_url"] == "https://linkedin.com/in/alice"
    assert data["luma_email"] == "alice_luma@example.com"
    assert "id" in data
    assert "created_at" in data


def test_signup_password_not_in_response(client: TestClient):
    """POST /auth/signup must NOT return password or luma_password."""
    payload = {
        "name": "Bob",
        "email": "bob@example.com",
        "password": "StrongP@ss1",
        "luma_password": "LumaSecret123",
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "password" not in data
    assert "password_hash" not in data
    assert "luma_password" not in data
    assert "luma_password_encrypted" not in data


def test_signup_duplicate_email(client: TestClient, registered_user: dict):
    """POST /auth/signup with an already-registered email returns 409."""
    payload = {
        "name": "Another User",
        "email": registered_user["email"],
        "password": "AnotherPass1!",
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


def test_signup_missing_name(client: TestClient):
    """Signup without name returns 422."""
    resp = client.post("/auth/signup", json={"email": "a@b.com", "password": "12345678"})
    assert resp.status_code == 422


def test_signup_missing_email(client: TestClient):
    """Signup without email returns 422."""
    resp = client.post("/auth/signup", json={"name": "X", "password": "12345678"})
    assert resp.status_code == 422


def test_signup_missing_password(client: TestClient):
    """Signup without password returns 422."""
    resp = client.post("/auth/signup", json={"name": "X", "email": "a@b.com"})
    assert resp.status_code == 422


def test_signup_invalid_email(client: TestClient):
    """Signup with malformed email returns 422."""
    resp = client.post(
        "/auth/signup", json={"name": "X", "email": "notanemail", "password": "12345678"}
    )
    assert resp.status_code == 422


def test_signup_short_password(client: TestClient):
    """Signup with password shorter than 8 characters returns 422."""
    resp = client.post(
        "/auth/signup", json={"name": "X", "email": "a@b.com", "password": "abc"}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


def test_login_success(client: TestClient, registered_user: dict):
    """POST /auth/login with valid credentials returns a JWT."""
    resp = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, registered_user: dict):
    """POST /auth/login with wrong password returns 401."""
    resp = client.post(
        "/auth/login",
        json={"email": registered_user["email"], "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_nonexistent_email(client: TestClient):
    """POST /auth/login with unknown email returns the SAME 401 error (no user enumeration)."""
    resp = client.post(
        "/auth/login",
        json={"email": "ghost@nowhere.com", "password": "DoesntMatter1"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


# ---------------------------------------------------------------------------
# GET /auth/me tests
# ---------------------------------------------------------------------------


def test_me_valid_token(client: TestClient, auth_token: str):
    """GET /auth/me with a valid JWT returns user profile."""
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_me_no_token(client: TestClient):
    """GET /auth/me without a token returns 401."""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(client: TestClient):
    """GET /auth/me with a garbage token returns 401."""
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401


def test_me_expired_token(client: TestClient, registered_user: dict):
    """GET /auth/me with an expired JWT returns 401."""
    # Build a token that expired 1 hour ago.
    payload = {
        "sub": str(registered_user["response"]["id"]),
        "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /token requires auth
# ---------------------------------------------------------------------------


def test_token_requires_auth(client: TestClient):
    """POST /token without a JWT returns 401."""
    resp = client.post("/token")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Luma password encrypted in DB
# ---------------------------------------------------------------------------


def test_luma_password_encrypted_in_db(client: TestClient):
    """After signup with Luma credentials, luma_password is encrypted (not plaintext) in DB."""
    from tests.conftest import TestingSessionLocal
    from agent.database import User

    plaintext_luma_pw = "MyLumaSecret!123"
    payload = {
        "name": "Encrypted User",
        "email": "enc@example.com",
        "password": "SecurePass1!",
        "luma_email": "enc_luma@example.com",
        "luma_password": plaintext_luma_pw,
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "enc@example.com").first()
        assert user is not None
        assert user.luma_password_encrypted is not None
        # Encrypted value must differ from plaintext
        assert user.luma_password_encrypted != plaintext_luma_pw
        # And the hash should look like a Fernet token (starts with 'gAAAAA')
        assert user.luma_password_encrypted.startswith("gAAAAA")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Password is bcrypt-hashed in DB
# ---------------------------------------------------------------------------


def test_password_hashed_bcrypt_in_db(client: TestClient):
    """After signup, the stored password_hash is a bcrypt hash, not plaintext."""
    from tests.conftest import TestingSessionLocal
    from agent.database import User

    payload = {
        "name": "Hash User",
        "email": "hash@example.com",
        "password": "MySecretPass1!",
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "hash@example.com").first()
        assert user is not None
        # bcrypt hashes start with $2b$ (or $2a$)
        assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
        assert user.password_hash != "MySecretPass1!"
    finally:
        db.close()
