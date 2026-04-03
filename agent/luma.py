import os

import httpx

LUMA_BASE_URL = "https://api.lu.ma/public/v1"


class LumaClient:
    """Wrapper around the Luma API for event discovery and registration."""

    def __init__(self):
        self.api_key = os.getenv("LUMA_API_KEY", "")
        self._client = httpx.AsyncClient(
            base_url=LUMA_BASE_URL,
            headers={"x-luma-api-key": self.api_key},
        )

    async def fetch_events(self, filters: dict | None = None) -> list[dict]:
        """Fetch upcoming Luma events, optionally filtered."""
        raise NotImplementedError

    async def get_user_calendar(self, email: str) -> list[dict]:
        """Get the user's existing Luma registrations for conflict checking."""
        raise NotImplementedError

    async def check_conflict(self, email: str, event_start: str, event_end: str) -> bool:
        """Return True if the user has a conflicting event in the given window."""
        raise NotImplementedError

    async def register_for_event(self, email: str, event_id: str) -> dict:
        """Register the user for a specific event by event ID."""
        raise NotImplementedError

    async def close(self):
        await self._client.aclose()
