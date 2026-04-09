import os

from dotenv import load_dotenv

# Load .env BEFORE any agent/ imports so that environment variables
# (e.g. JWT_SECRET_KEY) are available when those modules initialise.
load_dotenv()

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from livekit.api import AccessToken, VideoGrants
import uuid

from agent.auth import get_current_user, router as auth_router
from agent.database import User, init_db
from agent.luma import LumaClient
from agent.memory import MemoryClient

# Initialise the database (creates tables if they don't exist)
init_db()

app = FastAPI(title="Luma Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

luma_client = LumaClient()
memory_client = MemoryClient()

# Register auth routes
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/token")
async def create_token(request: Request, current_user: User = Depends(get_current_user)):
    """Generate a LiveKit access token for a frontend participant (requires JWT)."""
    room_name = f"luma-room-{uuid.uuid4().hex[:8]}"
    participant_identity = f"user-{uuid.uuid4().hex[:8]}"

    api_key = os.getenv("LIVEKIT_API_KEY", "")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    livekit_url = os.getenv("LIVEKIT_URL", "")

    token = AccessToken(api_key, api_secret) \
        .with_identity(participant_identity) \
        .with_name("User") \
        .with_grants(VideoGrants(
            room_join=True,
            room=room_name,
            can_publish_data=True,
        ))

    return JSONResponse({
        "serverUrl": livekit_url,
        "roomName": room_name,
        "participantToken": token.to_jwt(),
        "participantName": "User",
    })
