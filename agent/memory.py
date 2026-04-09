import os


class MemoryClient:
    """Wrapper around mem0 for reading and writing user preferences."""

    def __init__(self):
        self.api_key = os.getenv("MEM0_API_KEY", "")
        self._client = None
        if self.api_key:
            try:
                from mem0 import MemoryClient as Mem0Client
                self._client = Mem0Client(api_key=self.api_key)
            except ImportError:
                pass

    def get_preferences(self, user_email: str) -> list[str]:
        """Retrieve stored preference memories for a user."""
        raise NotImplementedError

    def record_registration(self, user_email: str, event_name: str, category: str, date: str) -> None:
        """Write a preference signal after a successful registration."""
        raise NotImplementedError

    def search(self, query: str, user_email: str) -> list[dict]:
        """Search user memories for preference signals relevant to a query."""
        raise NotImplementedError
