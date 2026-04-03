from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from agent.conversation import ConversationManager
from agent.luma import LumaClient
from agent.memory import MemoryClient

load_dotenv()

app = FastAPI(title="Luma Voice Agent")

conversation_manager = ConversationManager()
luma_client = LumaClient()
memory_client = MemoryClient()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    """ElevenLabs Conversational AI webhook handler.

    Receives tool call requests from the ElevenLabs agent and dispatches
    them to the appropriate handler based on the tool name.
    """
    payload = await request.json()
    tool_name = payload.get("tool_name")
    conversation_id = payload.get("conversation_id")
    parameters = payload.get("parameters", {})

    if tool_name == "fetch_events":
        return await handle_fetch_events(conversation_id, parameters)
    elif tool_name == "check_conflict":
        return await handle_check_conflict(conversation_id, parameters)
    elif tool_name == "register_event":
        return await handle_register_event(conversation_id, parameters)
    elif tool_name == "parse_email":
        return await handle_parse_email(conversation_id, parameters)

    return JSONResponse(status_code=400, content={"error": f"Unknown tool: {tool_name}"})


async def handle_fetch_events(conversation_id: str, parameters: dict) -> JSONResponse:
    """Fetch Luma events filtered by user preferences from mem0."""
    raise NotImplementedError


async def handle_check_conflict(conversation_id: str, parameters: dict) -> JSONResponse:
    """Check if the user has a scheduling conflict for a given event."""
    raise NotImplementedError


async def handle_register_event(conversation_id: str, parameters: dict) -> JSONResponse:
    """Register the user for a Luma event."""
    raise NotImplementedError


async def handle_parse_email(conversation_id: str, parameters: dict) -> JSONResponse:
    """Parse a spoken email string into a normalized email address."""
    raise NotImplementedError
