"""Playwright-based registration engine for Luma events.

Provides RegistrationService for automated event registration via headless
Chromium. Handles login, session caching, form detection, field mapping,
and submission.
"""

import asyncio
import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REGISTRATION_TIMEOUT_MS = 30_000  # 30 seconds
LUMA_SIGNIN_URL = "https://lu.ma/signin"
LUMA_HOME_URL = "https://lu.ma/home"

# Realistic browser viewport and user agent
VIEWPORT = {"width": 1280, "height": 720}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Directory for cached Playwright storageState files
SESSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "playwright_sessions",
)


# ---------------------------------------------------------------------------
# Pydantic result model
# ---------------------------------------------------------------------------


class RegistrationResult(BaseModel):
    """Structured result from an event registration attempt."""

    status: str  # registered | pending_approval | already_registered | needs_input | refused | failed
    event_name: str = ""
    unknown_fields: list[str] = []
    error: str | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# RegistrationService
# ---------------------------------------------------------------------------


class RegistrationService:
    """Manages Playwright-based Luma event registrations.

    Usage::

        service = RegistrationService()
        result = await service.register_for_event(user_id, event_url, profile)
        await service.cleanup()
    """

    # Maps lowercase canonical label fragments → profile dict keys.
    # When a form label contains a key, the corresponding profile value is used.
    FIELD_MAPPING: dict[str, str] = {
        "name": "name",
        "full name": "name",
        "first name": "name",
        "email": "email",
        "e-mail": "email",
        "linkedin": "linkedin_url",
        "company": "company",
        "organization": "company",
        "phone": "phone",
        "telephone": "phone",
        "mobile": "phone",
        "job title": "job_title",
        "title": "job_title",
        "role": "job_title",
        "twitter": "twitter_x",
        "x handle": "twitter_x",
        "x.com": "twitter_x",
    }

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sessions_dir = SESSIONS_DIR
        os.makedirs(self._sessions_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Session file helpers
    # ------------------------------------------------------------------

    def _session_path(self, user_id: str) -> str:
        """Return the file path for a user's cached storageState."""
        return os.path.join(self._sessions_dir, f"{user_id}.json")

    def _has_cached_session(self, user_id: str) -> bool:
        """Return True if a cached storageState file exists for the user."""
        return os.path.isfile(self._session_path(user_id))

    def _save_session(self, user_id: str, state: dict[str, Any]) -> None:
        """Persist Playwright storageState to disk."""
        path = self._session_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info("Saved session state for user %s", user_id)

    def _load_session(self, user_id: str) -> dict[str, Any] | None:
        """Load a cached storageState, returning *None* if absent or invalid."""
        path = self._session_path(user_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt session file for user %s — removing", user_id)
            os.remove(path)
            return None

    # ------------------------------------------------------------------
    # URL validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_event_url(url: str | None) -> bool:
        """Return True if *url* points to a lu.ma domain (http/https)."""
        if not url:
            return False
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        if parsed.scheme not in ("http", "https"):
            return False

        host = (parsed.hostname or "").lower()
        # Accept lu.ma and any subdomain (e.g. calendar.lu.ma, www.lu.ma)
        if host == "lu.ma" or host.endswith(".lu.ma"):
            return True
        return False

    # ------------------------------------------------------------------
    # Profile → form field mapping
    # ------------------------------------------------------------------

    def _map_profile_to_fields(self, profile: dict[str, Any]) -> dict[str, str]:
        """Build a mapping from canonical label fragments to profile values.

        Returns ``{label_fragment: value}`` for every profile field that has
        a non-empty value.
        """
        result: dict[str, str] = {}
        for label_key, profile_key in self.FIELD_MAPPING.items():
            value = profile.get(profile_key)
            if value:
                result[label_key] = str(value)
        return result

    # ------------------------------------------------------------------
    # Browser management
    # ------------------------------------------------------------------

    async def _get_browser(self) -> Browser:
        """Return (and lazily launch) the shared headless Chromium browser."""
        if self._browser is None or not self._browser.is_connected():
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def _create_browser_context(
        self, user_id: str
    ) -> tuple[BrowserContext, Page]:
        """Create a new browser context, optionally restoring cached session."""
        browser = await self._get_browser()
        storage = self._load_session(user_id)

        ctx_kwargs: dict[str, Any] = {
            "viewport": VIEWPORT,
            "user_agent": USER_AGENT,
        }
        if storage:
            ctx_kwargs["storage_state"] = storage

        context = await browser.new_context(**ctx_kwargs)
        context.set_default_timeout(REGISTRATION_TIMEOUT_MS)
        page = await context.new_page()
        return context, page

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login_to_luma(
        self, user_id: str, luma_email: str, luma_password: str
    ) -> bool:
        """Log into Luma and cache the storageState.

        Returns *True* on success, *False* on failure.
        """
        browser = await self._get_browser()
        context: BrowserContext | None = None
        page: Page | None = None
        try:
            context = await browser.new_context(
                viewport=VIEWPORT,
                user_agent=USER_AGENT,
            )
            context.set_default_timeout(REGISTRATION_TIMEOUT_MS)
            page = await context.new_page()

            # Navigate to Luma sign-in
            await page.goto(LUMA_SIGNIN_URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            # Fill email
            email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
            await email_input.first.fill(luma_email)

            # Click continue / next to proceed to password
            continue_btn = page.locator('button:has-text("Continue"), button:has-text("Sign In"), button:has-text("Next"), button[type="submit"]')
            await continue_btn.first.click()
            await page.wait_for_timeout(2000)

            # Fill password
            password_input = page.locator('input[type="password"]')
            await password_input.first.fill(luma_password)

            # Submit
            submit_btn = page.locator('button:has-text("Sign In"), button:has-text("Continue"), button:has-text("Log In"), button[type="submit"]')
            await submit_btn.first.click()

            # Wait for navigation away from sign-in
            await page.wait_for_url(
                lambda url: "signin" not in url.lower() and "login" not in url.lower(),
                timeout=REGISTRATION_TIMEOUT_MS,
            )

            # Save session state
            state = await context.storage_state()
            self._save_session(user_id, state)
            logger.info("Luma login successful for user %s", user_id)
            return True

        except (PlaywrightTimeoutError, Exception) as exc:
            logger.error("Luma login failed for user %s: %s", user_id, exc)
            return False
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    # ------------------------------------------------------------------
    # Session verification helpers
    # ------------------------------------------------------------------

    async def _ensure_logged_in(
        self,
        page: Page,
        context: BrowserContext,
        user_id: str,
        luma_email: str | None = None,
        luma_password: str | None = None,
    ) -> tuple[bool, BrowserContext, Page]:
        """Verify the session is valid; re-login if needed.

        Returns ``(logged_in, context, page)`` — the context and page may be
        replaced with fresh instances after a re-login so that subsequent
        navigation uses the updated storageState.
        """
        # Quick check: navigate to lu.ma and see if redirected to signin
        await page.goto("https://lu.ma/home", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        current_url = page.url.lower()
        if "signin" in current_url or "login" in current_url:
            # Session expired — try re-login if credentials provided
            if luma_email and luma_password:
                logger.info("Session expired for user %s, re-logging in", user_id)
                success = await self.login_to_luma(user_id, luma_email, luma_password)
                if not success:
                    return False, context, page
                # Re-login saved a fresh storageState to disk.  Close the
                # stale context/page and create new ones that load the
                # refreshed cookies so subsequent navigation is authenticated.
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await context.close()
                except Exception:
                    pass
                context, page = await self._create_browser_context(user_id)
                return True, context, page
            return False, context, page
        return True, context, page

    # ------------------------------------------------------------------
    # Event page helpers
    # ------------------------------------------------------------------

    async def _get_event_name(self, page: Page) -> str:
        """Extract the event name from the page."""
        try:
            # Try common selectors for the event title
            for selector in [
                'h1',
                '[class*="event-title"]',
                '[class*="EventTitle"]',
                'meta[property="og:title"]',
            ]:
                if selector.startswith("meta"):
                    el = await page.query_selector(selector)
                    if el:
                        return (await el.get_attribute("content")) or ""
                else:
                    el = page.locator(selector).first
                    if await el.count() > 0:
                        text = (await el.text_content() or "").strip()
                        if text:
                            return text
            # Fallback: page title
            title = await page.title()
            return title.replace(" · Luma", "").replace(" | Luma", "").strip()
        except Exception:
            return ""

    async def _detect_event_type(self, page: Page) -> str:
        """Detect whether an event is free, paid, or approval-required.

        Returns one of: ``'free'``, ``'paid'``, ``'approval_required'``,
        ``'not_found'``.
        """
        page_content = (await page.content()).lower()

        # Check for 404 / not found
        if "not found" in page_content or "404" in (await page.title()).lower():
            return "not_found"

        # Check for paid indicators (ticket prices, payment elements)
        paid_indicators = [
            'text="Buy Ticket"',
            'text="Purchase"',
            'text="Add to Cart"',
            '[class*="price"]',
            '[class*="ticket-price"]',
            '[data-testid*="price"]',
        ]
        for selector in paid_indicators:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    return "paid"
            except Exception:
                continue

        # Check page text for price patterns like $10, $25.00
        price_pattern = r'\$\d+(?:\.\d{2})?'
        # Only look for prices near ticket/registration context
        try:
            ticket_sections = page.locator('[class*="ticket"], [class*="Ticket"], [class*="pricing"], [class*="Pricing"]')
            if await ticket_sections.count() > 0:
                ticket_text = await ticket_sections.first.text_content() or ""
                if re.search(price_pattern, ticket_text):
                    return "paid"
        except Exception:
            pass

        # Check for approval-required indicators
        approval_indicators = [
            'text="Request to Join"',
            'text="Apply"',
            'text="Request Approval"',
            'text="Request an Invite"',
        ]
        for selector in approval_indicators:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    return "approval_required"
            except Exception:
                continue

        # Check page content for approval text
        approval_texts = [
            "requires approval",
            "request to join",
            "approval required",
            "pending approval",
            "request an invite",
        ]
        for text in approval_texts:
            if text in page_content:
                return "approval_required"

        return "free"

    async def _is_already_registered(self, page: Page) -> bool:
        """Return True if the user is already registered for this event."""
        already_indicators = [
            "text=\"You're Going\"",
            "text=\"You're going\"",
            'text="Going"',
            'text="Registered"',
            'text="You are registered"',
            'text="You\'re registered"',
        ]
        for selector in already_indicators:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    return True
            except Exception:
                continue

        page_content = await page.content()
        already_texts = [
            "you're going",
            "you are registered",
            "you're registered",
            "already registered",
        ]
        content_lower = page_content.lower()
        for text in already_texts:
            if text in content_lower:
                return True

        return False

    async def _click_register_button(self, page: Page) -> bool:
        """Find and click the Register/RSVP button.

        Returns *True* if a button was found and clicked.
        """
        register_selectors = [
            'button:has-text("Register")',
            'button:has-text("RSVP")',
            'button:has-text("Join")',
            'button:has-text("Attend")',
            'button:has-text("Sign Up")',
            'a:has-text("Register")',
            'a:has-text("RSVP")',
        ]
        for selector in register_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click()
                    await page.wait_for_timeout(2000)
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------
    # Form field processing
    # ------------------------------------------------------------------

    async def _process_form_fields(
        self,
        page: Page,
        profile_data: dict[str, Any],
        custom_field_answers: dict[str, str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Detect form fields, fill known ones, report unknown ones.

        Returns ``(all_filled, unknown_fields)`` where *all_filled* is True
        when every required field has been populated.
        """
        profile_map = self._map_profile_to_fields(profile_data)
        unknown_fields: list[str] = []

        # Find all input/textarea/select elements within the registration form
        form_fields = page.locator(
            'input:visible, textarea:visible, select:visible'
        )
        field_count = await form_fields.count()

        for i in range(field_count):
            field = form_fields.nth(i)
            try:
                field_type = (await field.get_attribute("type") or "text").lower()
                # Skip hidden, submit, and button fields
                if field_type in ("hidden", "submit", "button"):
                    continue

                # Try to find the label for this field
                field_id = await field.get_attribute("id") or ""
                field_name = await field.get_attribute("name") or ""
                field_placeholder = (
                    await field.get_attribute("placeholder") or ""
                )
                aria_label = await field.get_attribute("aria-label") or ""

                # Build a label string from available attributes
                label_text = ""
                if field_id:
                    # Look for a <label for="..."> element
                    label_el = page.locator(f'label[for="{field_id}"]')
                    if await label_el.count() > 0:
                        label_text = (
                            await label_el.first.text_content() or ""
                        ).strip()

                if not label_text:
                    label_text = aria_label or field_placeholder or field_name

                if not label_text:
                    continue

                label_lower = label_text.lower().strip()

                # Check if the field already has a value
                current_value = await field.input_value()
                if current_value and current_value.strip():
                    continue  # Already filled (e.g., from Luma profile)

                # Try to map from profile
                matched = False
                for key_fragment, value in profile_map.items():
                    if key_fragment in label_lower:
                        await field.fill(value)
                        matched = True
                        break

                if not matched:
                    # Check custom_field_answers
                    if custom_field_answers:
                        for answer_label, answer_value in custom_field_answers.items():
                            if answer_label.lower() in label_lower or label_lower in answer_label.lower():
                                await field.fill(answer_value)
                                matched = True
                                break

                if not matched:
                    # Check if field is actually required in the HTML
                    is_required = (
                        await field.get_attribute("required") is not None
                        or await field.get_attribute("aria-required") == "true"
                    )
                    if is_required:
                        # Truly required unknown field — blocks submission
                        unknown_fields.append(label_text)
                    else:
                        # Optional visible field — report but don't block
                        logger.debug(
                            "Optional unknown field skipped: %s", label_text
                        )

            except Exception as exc:
                logger.debug("Error processing form field %d: %s", i, exc)
                continue

        if unknown_fields:
            return False, unknown_fields
        return True, []

    async def _submit_and_confirm(
        self, page: Page, event_type: str
    ) -> RegistrationResult:
        """Submit the registration form and wait for confirmation."""
        event_name = await self._get_event_name(page)

        # Click submit button
        submit_selectors = [
            'button:has-text("Register")',
            'button:has-text("Submit")',
            'button:has-text("RSVP")',
            'button:has-text("Confirm")',
            'button:has-text("Join")',
            'button[type="submit"]',
        ]
        submitted = False
        for selector in submit_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.count() > 0 and await btn.is_enabled():
                    await btn.click()
                    submitted = True
                    break
            except Exception:
                continue

        if not submitted:
            return RegistrationResult(
                status="failed",
                event_name=event_name,
                error="Could not find submit button",
                message="Registration form submit button not found",
            )

        # Wait for confirmation
        await page.wait_for_timeout(3000)

        # Check for success indicators
        page_content = (await page.content()).lower()
        success_indicators = [
            "you're going",
            "you are registered",
            "you're registered",
            "registration confirmed",
            "see you there",
            "successfully registered",
            "you're in",
        ]

        for indicator in success_indicators:
            if indicator in page_content:
                if event_type == "approval_required":
                    return RegistrationResult(
                        status="pending_approval",
                        event_name=event_name,
                        message="Registration submitted, awaiting host approval",
                    )
                return RegistrationResult(
                    status="registered",
                    event_name=event_name,
                    message=f"Successfully registered for {event_name}",
                )

        # Check for pending approval
        approval_indicators = [
            "pending approval",
            "request submitted",
            "awaiting approval",
            "request sent",
            "host will review",
        ]
        for indicator in approval_indicators:
            if indicator in page_content:
                return RegistrationResult(
                    status="pending_approval",
                    event_name=event_name,
                    message="Registration submitted, awaiting host approval",
                )

        # Check for error indicators
        error_indicators = [
            "something went wrong",
            "error",
            "try again",
            "failed",
        ]
        for indicator in error_indicators:
            if indicator in page_content:
                return RegistrationResult(
                    status="failed",
                    event_name=event_name,
                    error="Registration submission failed",
                    message="The registration form reported an error",
                )

        # If no clear indicator, assume success (form submitted without error)
        if event_type == "approval_required":
            return RegistrationResult(
                status="pending_approval",
                event_name=event_name,
                message="Registration submitted, awaiting host approval",
            )
        return RegistrationResult(
            status="registered",
            event_name=event_name,
            message=f"Successfully registered for {event_name}",
        )

    # ------------------------------------------------------------------
    # Main registration flow
    # ------------------------------------------------------------------

    async def register_for_event(
        self,
        user_id: str,
        event_url: str,
        profile_data: dict[str, Any],
        custom_field_answers: dict[str, str] | None = None,
    ) -> RegistrationResult:
        """Register the user for a Luma event.

        Parameters
        ----------
        user_id:
            Unique user identifier (for session caching).
        event_url:
            The full URL of the Luma event page.
        profile_data:
            Dict with keys: name, email, linkedin_url, job_title, company,
            phone, twitter_x.
        custom_field_answers:
            Optional dict mapping custom field labels to values (for retries).

        Returns
        -------
        RegistrationResult
            Structured result with status, event_name, unknown_fields, etc.
        """
        # Validate URL before launching any browser
        if not self._validate_event_url(event_url):
            return RegistrationResult(
                status="failed",
                error="Invalid URL: only lu.ma event URLs are accepted",
                message="The provided URL is not a valid lu.ma event URL",
            )

        context: BrowserContext | None = None
        page: Page | None = None
        try:
            context, page = await self._create_browser_context(user_id)

            # Ensure we're logged in
            luma_email = profile_data.get("luma_email")
            luma_password = profile_data.get("luma_password")
            logged_in, context, page = await self._ensure_logged_in(
                page, context, user_id, luma_email, luma_password
            )
            if not logged_in:
                return RegistrationResult(
                    status="failed",
                    error="Luma login failed",
                    message="Could not log into Luma. Please check your credentials.",
                )

            # Navigate to event page
            await page.goto(event_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Get event name
            event_name = await self._get_event_name(page)

            # Detect event type
            event_type = await self._detect_event_type(page)

            if event_type == "not_found":
                return RegistrationResult(
                    status="failed",
                    event_name=event_name,
                    error="Event not found",
                    message="The event page could not be found (404)",
                )

            if event_type == "paid":
                return RegistrationResult(
                    status="refused",
                    event_name=event_name,
                    error="paid_event",
                    message="Cannot register for paid events automatically",
                )

            # Check if already registered
            if await self._is_already_registered(page):
                return RegistrationResult(
                    status="already_registered",
                    event_name=event_name,
                    message=f"You are already registered for {event_name}",
                )

            # Click the register button
            clicked = await self._click_register_button(page)
            if not clicked:
                return RegistrationResult(
                    status="failed",
                    event_name=event_name,
                    error="Register button not found",
                    message="Could not find a registration button on the event page",
                )

            # Process form fields
            all_filled, unknown = await self._process_form_fields(
                page, profile_data, custom_field_answers
            )

            if not all_filled and unknown:
                return RegistrationResult(
                    status="needs_input",
                    event_name=event_name,
                    unknown_fields=unknown,
                    message="Custom fields need your input before registration can proceed",
                )

            # Submit and confirm
            result = await self._submit_and_confirm(page, event_type)

            # Save updated session state after successful interaction
            if context:
                try:
                    state = await context.storage_state()
                    self._save_session(user_id, state)
                except Exception:
                    pass

            return result

        except PlaywrightTimeoutError:
            return RegistrationResult(
                status="failed",
                error="Registration timed out after 30 seconds",
                message="The registration process timed out. Please try again later.",
            )
        except Exception as exc:
            logger.error("Registration error for user %s: %s", user_id, exc)
            return RegistrationResult(
                status="failed",
                error=str(exc),
                message="An unexpected error occurred during registration",
            )
        finally:
            # Always clean up browser context
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cleanup(self) -> None:
        """Close the browser and Playwright instance."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("RegistrationService cleaned up")
