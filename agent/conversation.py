from enum import Enum


class ConversationState(str, Enum):
    AWAIT_EMAIL = "AWAIT_EMAIL"
    AWAIT_EMAIL_CONFIRM = "AWAIT_EMAIL_CONFIRM"
    AWAIT_PICK = "AWAIT_PICK"
    AWAIT_CONFIRM = "AWAIT_CONFIRM"
    DONE = "DONE"


class SessionData:
    """Holds per-session state for a single conversation."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.state = ConversationState.AWAIT_EMAIL
        self.email: str | None = None
        self.events: list[dict] = []
        self.selected_event: dict | None = None


class ConversationManager:
    """Manages conversation state across sessions.

    Tracks state per conversation_id so the server never relies on the
    LLM to remember state across turns.
    """

    def __init__(self):
        self._sessions: dict[str, SessionData] = {}

    def get_or_create_session(self, conversation_id: str) -> SessionData:
        """Return existing session or create a new one."""
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = SessionData(conversation_id)
        return self._sessions[conversation_id]

    def transition(self, conversation_id: str, new_state: ConversationState) -> None:
        """Move a session to a new state."""
        session = self.get_or_create_session(conversation_id)
        session.state = new_state

    def remove_session(self, conversation_id: str) -> None:
        """Clean up a finished session."""
        self._sessions.pop(conversation_id, None)
