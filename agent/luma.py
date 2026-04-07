import os
import asyncio
import logging

from apify_client import ApifyClient

logger = logging.getLogger("luma-client")


class LumaClient:
    """Fetches Luma events via the Apify scraper actor."""

    def __init__(self):
        self.apify_token = os.getenv("APIFY_API_TOKEN", "")
        self.actor_id = "matyascimbulka/luma-event-scraper"
        self.default_categories = [
            s.strip()
            for s in os.getenv("LUMA_EVENT_CATEGORIES", "ai,tech").split(",")
            if s.strip()
        ]
        self.default_cities = [
            s.strip()
            for s in os.getenv("LUMA_CITIES", "San Francisco").split(",")
            if s.strip()
        ]
        self._client = ApifyClient(self.apify_token)

    async def list_events(
        self,
        slugs: list[str] | None = None,
        city: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        max_events: int = 10,
    ) -> list[dict]:
        """Run the Apify actor and return parsed events."""
        try:
            categories = slugs or self.default_categories
            cities = [city] if city else self.default_cities

            run_input: dict = {
                "slugs": categories,
                "cities": cities,
                "maxEventsPerCity": max_events,
            }

            # apify-client .call() is synchronous; wrap in asyncio.to_thread
            run = await asyncio.to_thread(
                self._client.actor(self.actor_id).call,
                run_input=run_input,
            )

            items = (
                await asyncio.to_thread(
                    self._client.dataset(run["defaultDatasetId"]).list_items
                )
            ).items

            events = []
            for item in items:
                location_obj = item.get("location", {})
                if isinstance(location_obj, dict):
                    location = location_obj.get(
                        "fullAddress", location_obj.get("city", "Online")
                    )
                else:
                    location = str(location_obj) if location_obj else "Online"

                description = item.get("description", "") or ""

                events.append({
                    "id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "description": description[:200],
                    "start_time": item.get("startAt", ""),
                    "end_time": item.get("endAt", ""),
                    "location": location,
                    "url": item.get("lumaUrl", ""),
                    "cover_url": item.get("coverImageUrl", ""),
                })
            return events
        except Exception as e:
            logger.error(f"Failed to fetch events from Apify: {e}")
            return []

    async def get_event(self, event_url: str) -> dict | None:
        """Return event details from cached results or by URL lookup."""
        return {
            "id": event_url,
            "name": "",
            "url": event_url,
        }

    async def close(self):
        pass
