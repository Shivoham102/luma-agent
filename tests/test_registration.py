"""Tests for the Playwright-based registration engine (agent/registration.py).

All tests mock Playwright — no real browser or network calls.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest")

from agent.registration import RegistrationResult, RegistrationService


# ---------------------------------------------------------------------------
# RegistrationResult Pydantic model tests
# ---------------------------------------------------------------------------


class TestRegistrationResult:
    """Validate the RegistrationResult Pydantic model."""

    def test_registered_result(self):
        result = RegistrationResult(
            status="registered",
            event_name="AI Meetup",
            unknown_fields=[],
            error=None,
            message="Successfully registered",
        )
        assert result.status == "registered"
        assert result.event_name == "AI Meetup"
        assert result.unknown_fields == []
        assert result.error is None
        assert result.message == "Successfully registered"

    def test_needs_input_result(self):
        result = RegistrationResult(
            status="needs_input",
            event_name="Hackathon",
            unknown_fields=["Dietary restrictions", "T-shirt size"],
            error=None,
            message="Custom fields need input",
        )
        assert result.status == "needs_input"
        assert len(result.unknown_fields) == 2
        assert "Dietary restrictions" in result.unknown_fields

    def test_refused_result(self):
        result = RegistrationResult(
            status="refused",
            event_name="Paid Conference",
            unknown_fields=[],
            error="paid_event",
            message="Cannot register for paid events",
        )
        assert result.status == "refused"
        assert result.error == "paid_event"

    def test_failed_result(self):
        result = RegistrationResult(
            status="failed",
            event_name="",
            unknown_fields=[],
            error="Timeout waiting for page",
            message="Registration failed",
        )
        assert result.status == "failed"
        assert result.error == "Timeout waiting for page"

    def test_pending_approval_result(self):
        result = RegistrationResult(
            status="pending_approval",
            event_name="VIP Event",
            unknown_fields=[],
            error=None,
            message="Awaiting host approval",
        )
        assert result.status == "pending_approval"

    def test_already_registered_result(self):
        result = RegistrationResult(
            status="already_registered",
            event_name="AI Meetup",
            unknown_fields=[],
            error=None,
            message="You are already registered",
        )
        assert result.status == "already_registered"

    def test_default_values(self):
        result = RegistrationResult(status="registered", message="ok")
        assert result.event_name == ""
        assert result.unknown_fields == []
        assert result.error is None

    def test_model_serialization(self):
        result = RegistrationResult(
            status="registered",
            event_name="Test",
            unknown_fields=[],
            error=None,
            message="Done",
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["status"] == "registered"
        assert data["event_name"] == "Test"


# ---------------------------------------------------------------------------
# URL validation tests
# ---------------------------------------------------------------------------


class TestURLValidation:
    """Test that invalid URLs are rejected before launching a browser."""

    def setup_method(self):
        self.service = RegistrationService()

    def test_valid_luma_url(self):
        assert self.service._validate_event_url("https://lu.ma/my-event") is True

    def test_valid_luma_url_http(self):
        assert self.service._validate_event_url("http://lu.ma/my-event") is True

    def test_valid_luma_url_www(self):
        assert self.service._validate_event_url("https://www.lu.ma/my-event") is True

    def test_invalid_domain_google(self):
        assert self.service._validate_event_url("https://google.com/event") is False

    def test_invalid_domain_similar(self):
        assert self.service._validate_event_url("https://lu.ma.evil.com/event") is False

    def test_empty_url(self):
        assert self.service._validate_event_url("") is False

    def test_none_url(self):
        assert self.service._validate_event_url(None) is False

    def test_no_scheme(self):
        assert self.service._validate_event_url("lu.ma/event") is False

    def test_just_domain(self):
        assert self.service._validate_event_url("https://lu.ma") is True

    def test_subdomain_luma(self):
        # lu.ma might have subdomains like calendar.lu.ma
        assert self.service._validate_event_url("https://calendar.lu.ma/event") is True

    def test_invalid_scheme(self):
        assert self.service._validate_event_url("ftp://lu.ma/event") is False


# ---------------------------------------------------------------------------
# Session file management tests
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Test session file save/load/check for Playwright storageState."""

    def setup_method(self):
        self.service = RegistrationService()
        # Use a temp directory for tests
        self.test_sessions_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "playwright_sessions",
        )
        self.service._sessions_dir = self.test_sessions_dir
        os.makedirs(self.test_sessions_dir, exist_ok=True)

    def teardown_method(self):
        # Clean up test session files
        test_file = os.path.join(self.test_sessions_dir, "test_user_123.json")
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_session_path_generation(self):
        path = self.service._session_path("user_42")
        assert path.endswith("user_42.json")
        assert "playwright_sessions" in path

    def test_has_cached_session_false_when_no_file(self):
        assert self.service._has_cached_session("nonexistent_user") is False

    def test_has_cached_session_true_when_file_exists(self):
        path = self.service._session_path("test_user_123")
        with open(path, "w") as f:
            json.dump({"cookies": []}, f)
        assert self.service._has_cached_session("test_user_123") is True

    def test_save_and_load_session(self):
        user_id = "test_user_123"
        state = {"cookies": [{"name": "session", "value": "abc"}], "origins": []}
        self.service._save_session(user_id, state)

        loaded = self.service._load_session(user_id)
        assert loaded is not None
        assert loaded["cookies"][0]["name"] == "session"

    def test_load_session_returns_none_when_missing(self):
        loaded = self.service._load_session("nonexistent_user")
        assert loaded is None


# ---------------------------------------------------------------------------
# Registration flow tests (mocked Playwright)
# ---------------------------------------------------------------------------


class TestRegistrationFlow:
    """Test the registration flow with mocked Playwright."""

    def setup_method(self):
        self.service = RegistrationService()
        self.profile_data = {
            "name": "Test User",
            "email": "test@example.com",
            "linkedin_url": "https://linkedin.com/in/test",
            "job_title": "Engineer",
            "company": "TestCorp",
            "phone": "+1234567890",
            "twitter_x": "@testuser",
        }

    @pytest.mark.asyncio
    async def test_register_rejects_non_luma_url(self):
        """Registration with non-lu.ma URL should fail without launching browser."""
        result = await self.service.register_for_event(
            user_id="1",
            event_url="https://google.com/event",
            profile_data=self.profile_data,
        )
        assert result.status == "failed"
        assert "invalid" in result.error.lower() or "lu.ma" in result.error.lower()

    @pytest.mark.asyncio
    async def test_register_rejects_empty_url(self):
        """Registration with empty URL should fail."""
        result = await self.service.register_for_event(
            user_id="1",
            event_url="",
            profile_data=self.profile_data,
        )
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_register_detects_paid_event(self):
        """If the event page shows payment/pricing, refuse with paid_event."""
        mock_page = AsyncMock()
        mock_page.title.return_value = "Premium AI Conference · Luma"
        mock_page.url = "https://lu.ma/premium-conf"
        # Simulate paid event detection: ticket selector visible
        mock_page.locator.return_value.count.return_value = 1
        mock_page.query_selector.return_value = None

        with patch.object(
            self.service, "_create_browser_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_browser_ctx = AsyncMock()
            mock_browser_ctx.new_page.return_value = mock_page
            mock_ctx.return_value = (mock_browser_ctx, mock_page)

            with patch.object(
                self.service, "_ensure_logged_in", new_callable=AsyncMock
            ) as mock_login:
                mock_login.return_value = True

                with patch.object(
                    self.service, "_detect_event_type", new_callable=AsyncMock
                ) as mock_detect:
                    mock_detect.return_value = "paid"

                    with patch.object(
                        self.service, "_get_event_name", new_callable=AsyncMock
                    ) as mock_name:
                        mock_name.return_value = "Premium AI Conference"

                        result = await self.service.register_for_event(
                            user_id="1",
                            event_url="https://lu.ma/premium-conf",
                            profile_data=self.profile_data,
                        )
                        assert result.status == "refused"
                        assert "paid" in result.error.lower()

    @pytest.mark.asyncio
    async def test_register_detects_already_registered(self):
        """If user is already registered, return already_registered status."""
        with patch.object(
            self.service, "_create_browser_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_page = AsyncMock()
            mock_browser_ctx = AsyncMock()
            mock_browser_ctx.new_page.return_value = mock_page
            mock_ctx.return_value = (mock_browser_ctx, mock_page)

            with patch.object(
                self.service, "_ensure_logged_in", new_callable=AsyncMock
            ) as mock_login:
                mock_login.return_value = True

                with patch.object(
                    self.service, "_detect_event_type", new_callable=AsyncMock
                ) as mock_detect:
                    mock_detect.return_value = "free"

                    with patch.object(
                        self.service, "_get_event_name", new_callable=AsyncMock
                    ) as mock_name:
                        mock_name.return_value = "AI Meetup"

                        with patch.object(
                            self.service,
                            "_is_already_registered",
                            new_callable=AsyncMock,
                        ) as mock_already:
                            mock_already.return_value = True

                            result = await self.service.register_for_event(
                                user_id="1",
                                event_url="https://lu.ma/ai-meetup",
                                profile_data=self.profile_data,
                            )
                            assert result.status == "already_registered"

    @pytest.mark.asyncio
    async def test_register_returns_unknown_fields(self):
        """If required custom fields exist, return needs_input with field list."""
        with patch.object(
            self.service, "_create_browser_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_page = AsyncMock()
            mock_browser_ctx = AsyncMock()
            mock_browser_ctx.new_page.return_value = mock_page
            mock_ctx.return_value = (mock_browser_ctx, mock_page)

            with patch.object(
                self.service, "_ensure_logged_in", new_callable=AsyncMock
            ) as mock_login:
                mock_login.return_value = True

                with patch.object(
                    self.service, "_detect_event_type", new_callable=AsyncMock
                ) as mock_detect:
                    mock_detect.return_value = "free"

                    with patch.object(
                        self.service, "_get_event_name", new_callable=AsyncMock
                    ) as mock_name:
                        mock_name.return_value = "Hackathon"

                        with patch.object(
                            self.service,
                            "_is_already_registered",
                            new_callable=AsyncMock,
                        ) as mock_already:
                            mock_already.return_value = False

                            with patch.object(
                                self.service,
                                "_click_register_button",
                                new_callable=AsyncMock,
                            ) as mock_click:
                                mock_click.return_value = True

                                with patch.object(
                                    self.service,
                                    "_process_form_fields",
                                    new_callable=AsyncMock,
                                ) as mock_fields:
                                    mock_fields.return_value = (
                                        False,
                                        ["Dietary restrictions", "T-shirt size"],
                                    )

                                    result = await self.service.register_for_event(
                                        user_id="1",
                                        event_url="https://lu.ma/hackathon",
                                        profile_data=self.profile_data,
                                    )
                                    assert result.status == "needs_input"
                                    assert "Dietary restrictions" in result.unknown_fields
                                    assert "T-shirt size" in result.unknown_fields

    @pytest.mark.asyncio
    async def test_register_successful(self):
        """Successful free event registration returns registered status."""
        with patch.object(
            self.service, "_create_browser_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_page = AsyncMock()
            mock_browser_ctx = AsyncMock()
            mock_browser_ctx.new_page.return_value = mock_page
            mock_ctx.return_value = (mock_browser_ctx, mock_page)

            with patch.object(
                self.service, "_ensure_logged_in", new_callable=AsyncMock
            ) as mock_login:
                mock_login.return_value = True

                with patch.object(
                    self.service, "_detect_event_type", new_callable=AsyncMock
                ) as mock_detect:
                    mock_detect.return_value = "free"

                    with patch.object(
                        self.service, "_get_event_name", new_callable=AsyncMock
                    ) as mock_name:
                        mock_name.return_value = "AI Meetup"

                        with patch.object(
                            self.service,
                            "_is_already_registered",
                            new_callable=AsyncMock,
                        ) as mock_already:
                            mock_already.return_value = False

                            with patch.object(
                                self.service,
                                "_click_register_button",
                                new_callable=AsyncMock,
                            ) as mock_click:
                                mock_click.return_value = True

                                with patch.object(
                                    self.service,
                                    "_process_form_fields",
                                    new_callable=AsyncMock,
                                ) as mock_fields:
                                    mock_fields.return_value = (True, [])

                                    with patch.object(
                                        self.service,
                                        "_submit_and_confirm",
                                        new_callable=AsyncMock,
                                    ) as mock_submit:
                                        mock_submit.return_value = RegistrationResult(
                                            status="registered",
                                            event_name="AI Meetup",
                                            unknown_fields=[],
                                            error=None,
                                            message="Successfully registered for AI Meetup",
                                        )

                                        result = await self.service.register_for_event(
                                            user_id="1",
                                            event_url="https://lu.ma/ai-meetup",
                                            profile_data=self.profile_data,
                                        )
                                        assert result.status == "registered"
                                        assert result.event_name == "AI Meetup"

    @pytest.mark.asyncio
    async def test_register_approval_required(self):
        """Approval-required event returns pending_approval status."""
        with patch.object(
            self.service, "_create_browser_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_page = AsyncMock()
            mock_browser_ctx = AsyncMock()
            mock_browser_ctx.new_page.return_value = mock_page
            mock_ctx.return_value = (mock_browser_ctx, mock_page)

            with patch.object(
                self.service, "_ensure_logged_in", new_callable=AsyncMock
            ) as mock_login:
                mock_login.return_value = True

                with patch.object(
                    self.service, "_detect_event_type", new_callable=AsyncMock
                ) as mock_detect:
                    mock_detect.return_value = "approval_required"

                    with patch.object(
                        self.service, "_get_event_name", new_callable=AsyncMock
                    ) as mock_name:
                        mock_name.return_value = "VIP Event"

                        with patch.object(
                            self.service,
                            "_is_already_registered",
                            new_callable=AsyncMock,
                        ) as mock_already:
                            mock_already.return_value = False

                            with patch.object(
                                self.service,
                                "_click_register_button",
                                new_callable=AsyncMock,
                            ) as mock_click:
                                mock_click.return_value = True

                                with patch.object(
                                    self.service,
                                    "_process_form_fields",
                                    new_callable=AsyncMock,
                                ) as mock_fields:
                                    mock_fields.return_value = (True, [])

                                    with patch.object(
                                        self.service,
                                        "_submit_and_confirm",
                                        new_callable=AsyncMock,
                                    ) as mock_submit:
                                        mock_submit.return_value = RegistrationResult(
                                            status="pending_approval",
                                            event_name="VIP Event",
                                            unknown_fields=[],
                                            error=None,
                                            message="Registration submitted, awaiting host approval",
                                        )

                                        result = await self.service.register_for_event(
                                            user_id="1",
                                            event_url="https://lu.ma/vip-event",
                                            profile_data=self.profile_data,
                                        )
                                        assert result.status == "pending_approval"

    @pytest.mark.asyncio
    async def test_cleanup_closes_playwright(self):
        """cleanup() should close the playwright instance if initialized."""
        service = RegistrationService()
        mock_pw = AsyncMock()
        service._playwright = mock_pw
        mock_browser = AsyncMock()
        service._browser = mock_browser

        await service.cleanup()

        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()
        assert service._playwright is None
        assert service._browser is None


# ---------------------------------------------------------------------------
# Login flow tests (mocked)
# ---------------------------------------------------------------------------


class TestLoginFlow:
    """Test the Luma login flow with mocked Playwright."""

    def setup_method(self):
        self.service = RegistrationService()

    @pytest.mark.asyncio
    async def test_login_saves_storage_state(self):
        """Successful login should save storageState to disk."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_url = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.url = "https://lu.ma/home"
        mock_page.close = AsyncMock()

        # Set up locator chaining: page.locator(...).first → mock with .fill/.click
        mock_email_locator = AsyncMock()
        mock_email_first = AsyncMock()
        mock_email_locator.first = mock_email_first
        mock_email_first.fill = AsyncMock()

        mock_continue_locator = AsyncMock()
        mock_continue_first = AsyncMock()
        mock_continue_locator.first = mock_continue_first
        mock_continue_first.click = AsyncMock()

        mock_password_locator = AsyncMock()
        mock_password_first = AsyncMock()
        mock_password_locator.first = mock_password_first
        mock_password_first.fill = AsyncMock()

        mock_submit_locator = AsyncMock()
        mock_submit_first = AsyncMock()
        mock_submit_locator.first = mock_submit_first
        mock_submit_first.click = AsyncMock()

        call_count = {"value": 0}

        def locator_side_effect(selector):
            call_count["value"] += 1
            n = call_count["value"]
            if n == 1:
                return mock_email_locator
            elif n == 2:
                return mock_continue_locator
            elif n == 3:
                return mock_password_locator
            else:
                return mock_submit_locator

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_context.storage_state.return_value = {
            "cookies": [{"name": "session", "value": "abc"}],
            "origins": [],
        }
        mock_context.set_default_timeout = MagicMock()
        mock_context.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        with patch.object(
            self.service, "_get_browser", new_callable=AsyncMock
        ) as mock_get_browser:
            mock_get_browser.return_value = mock_browser

            result = await self.service.login_to_luma(
                user_id="test_login_user",
                luma_email="test@example.com",
                luma_password="password123",
            )

            assert result is True
            # Verify storage state was saved
            session_path = self.service._session_path("test_login_user")
            assert os.path.exists(session_path)

            # Clean up
            if os.path.exists(session_path):
                os.remove(session_path)

    @pytest.mark.asyncio
    async def test_login_failure_returns_false(self):
        """Failed login (e.g., wrong credentials) should return False."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_url = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.url = "https://lu.ma/signin"
        mock_page.close = AsyncMock()

        # Set up locator chaining
        mock_locator = AsyncMock()
        mock_first = AsyncMock()
        mock_locator.first = mock_first
        mock_first.fill = AsyncMock()
        mock_first.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        mock_context.close = AsyncMock()
        mock_context.set_default_timeout = MagicMock()

        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context

        with patch.object(
            self.service, "_get_browser", new_callable=AsyncMock
        ) as mock_get_browser:
            mock_get_browser.return_value = mock_browser

            result = await self.service.login_to_luma(
                user_id="test_fail_user",
                luma_email="wrong@example.com",
                luma_password="wrongpassword",
            )

            assert result is False


# ---------------------------------------------------------------------------
# Profile field mapping tests
# ---------------------------------------------------------------------------


class TestFieldMapping:
    """Test that profile fields map correctly to form field labels."""

    def setup_method(self):
        self.service = RegistrationService()

    def test_known_field_mapping(self):
        """Known fields should have correct mapping."""
        mapping = self.service.FIELD_MAPPING
        assert "name" in mapping or "Name" in mapping
        assert "email" in mapping or "Email" in mapping

    def test_profile_data_extraction(self):
        """Profile data should be extractable for form filling."""
        profile = {
            "name": "Test User",
            "email": "test@example.com",
            "linkedin_url": "https://linkedin.com/in/test",
            "job_title": "Engineer",
            "company": "TestCorp",
            "phone": "+1234567890",
            "twitter_x": "@testuser",
        }
        mapped = self.service._map_profile_to_fields(profile)
        assert len(mapped) > 0
        # Should have at least name and email
        found_name = False
        found_email = False
        for label, value in mapped.items():
            if value == "Test User":
                found_name = True
            if value == "test@example.com":
                found_email = True
        assert found_name, "Name should be mapped"
        assert found_email, "Email should be mapped"
