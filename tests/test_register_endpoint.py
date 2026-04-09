"""Tests for the POST /api/register endpoint."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from agent.registration import RegistrationResult


# ---------------------------------------------------------------------------
# Auth tests (VAL-REG-001)
# ---------------------------------------------------------------------------


def test_register_requires_auth(client: TestClient):
    """POST /api/register without JWT returns 401."""
    resp = client.post("/api/register", json={"event_url": "https://lu.ma/test"})
    assert resp.status_code == 401


def test_register_expired_token(client: TestClient, registered_user: dict):
    """POST /api/register with expired JWT returns 401."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from agent.auth import JWT_ALGORITHM, JWT_SECRET_KEY

    payload = {
        "sub": str(registered_user["response"]["id"]),
        "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    resp = client.post(
        "/api/register",
        json={"event_url": "https://lu.ma/test"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


def test_register_invalid_token(client: TestClient):
    """POST /api/register with garbage token returns 401."""
    resp = client.post(
        "/api/register",
        json={"event_url": "https://lu.ma/test"},
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Validation tests (VAL-REG-002)
# ---------------------------------------------------------------------------


def test_register_missing_event_url(client: TestClient, auth_token: str):
    """POST /api/register without event_url returns 422."""
    resp = client.post(
        "/api/register",
        json={},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


def test_register_null_event_url(client: TestClient, auth_token: str):
    """POST /api/register with null event_url returns 422."""
    resp = client.post(
        "/api/register",
        json={"event_url": None},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Missing Luma credentials (400)
# ---------------------------------------------------------------------------


def test_register_no_luma_credentials(client: TestClient, auth_token: str):
    """POST /api/register returns 400 when user has no Luma credentials."""
    # registered_user fixture creates a user without luma_email/luma_password
    resp = client.post(
        "/api/register",
        json={"event_url": "https://lu.ma/test-event"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "luma credentials" in data["detail"].lower()


# ---------------------------------------------------------------------------
# Successful registration (mock RegistrationService)
# ---------------------------------------------------------------------------


TEST_PASSWORD = "test-pass-12345678"  # noqa: S105 — test-only credential
TEST_LUMA_PASSWORD = "test-luma-pw-1234"  # noqa: S105 — test-only credential


def _create_user_with_luma_creds(client: TestClient) -> str:
    """Create a user with Luma credentials and return the auth token."""
    payload = {
        "name": "Luma User",
        "email": "luma@example.com",
        "password": TEST_PASSWORD,
        "linkedin_url": "https://linkedin.com/in/luma",
        "job_title": "Engineer",
        "company": "LumaCorp",
        "phone": "+1234567890",
        "twitter_x": "@lumauser",
        "luma_email": "luma@luma.com",
        "luma_password": TEST_LUMA_PASSWORD,
    }
    resp = client.post("/auth/signup", json=payload)
    assert resp.status_code == 201

    resp = client.post(
        "/auth/login",
        json={"email": "luma@example.com", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_register_success(client: TestClient):
    """POST /api/register with valid data calls RegistrationService and returns result."""
    token = _create_user_with_luma_creds(client)

    mock_result = RegistrationResult(
        status="registered",
        event_name="AI Meetup",
        message="Successfully registered for AI Meetup",
    )

    with patch(
        "main.RegistrationService.register_for_event",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_register:
        resp = client.post(
            "/api/register",
            json={"event_url": "https://lu.ma/ai-meetup"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert data["event_name"] == "AI Meetup"

        # Verify RegistrationService was called with correct args
        mock_register.assert_called_once()
        call_args = mock_register.call_args
        assert call_args[1]["event_url"] == "https://lu.ma/ai-meetup"
        assert call_args[1]["profile_data"]["name"] == "Luma User"
        assert call_args[1]["profile_data"]["email"] == "luma@example.com"
        assert call_args[1]["profile_data"]["luma_email"] == "luma@luma.com"
        # luma_password should be decrypted
        assert call_args[1]["profile_data"]["luma_password"] == TEST_LUMA_PASSWORD


def test_register_with_custom_field_answers(client: TestClient):
    """POST /api/register passes custom_field_answers to RegistrationService."""
    token = _create_user_with_luma_creds(client)

    mock_result = RegistrationResult(
        status="registered",
        event_name="Custom Event",
        message="Registered",
    )

    with patch(
        "main.RegistrationService.register_for_event",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_register:
        resp = client.post(
            "/api/register",
            json={
                "event_url": "https://lu.ma/custom-event",
                "custom_field_answers": {"Dietary restrictions": "Vegan"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        mock_register.assert_called_once()
        call_args = mock_register.call_args
        assert call_args[1]["custom_field_answers"] == {"Dietary restrictions": "Vegan"}


def test_register_needs_input(client: TestClient):
    """POST /api/register returns unknown_fields when RegistrationService reports needs_input."""
    token = _create_user_with_luma_creds(client)

    mock_result = RegistrationResult(
        status="needs_input",
        event_name="Custom Event",
        unknown_fields=["Dietary restrictions", "T-shirt size"],
        message="Custom fields need your input",
    )

    with patch(
        "main.RegistrationService.register_for_event",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_register:
        resp = client.post(
            "/api/register",
            json={"event_url": "https://lu.ma/custom-event"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "needs_input"
        assert "Dietary restrictions" in data["unknown_fields"]
        assert "T-shirt size" in data["unknown_fields"]


def test_register_profile_fields_passed(client: TestClient):
    """POST /api/register passes all profile fields to RegistrationService."""
    token = _create_user_with_luma_creds(client)

    mock_result = RegistrationResult(
        status="registered",
        event_name="Test",
        message="ok",
    )

    with patch(
        "main.RegistrationService.register_for_event",
        new_callable=AsyncMock,
        return_value=mock_result,
    ) as mock_register:
        resp = client.post(
            "/api/register",
            json={"event_url": "https://lu.ma/test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        call_args = mock_register.call_args
        profile = call_args[1]["profile_data"]
        assert profile["linkedin_url"] == "https://linkedin.com/in/luma"
        assert profile["job_title"] == "Engineer"
        assert profile["company"] == "LumaCorp"
        assert profile["phone"] == "+1234567890"
        assert profile["twitter_x"] == "@lumauser"
