import os

from dotenv import load_dotenv

# Load .env BEFORE any agent/ imports so that environment variables
# (e.g. JWT_SECRET_KEY) are available when those modules initialise.
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from livekit.api import AccessToken, VideoGrants
from pydantic import BaseModel
import uuid

from agent.auth import decrypt_luma_password, get_current_user, router as auth_router
from agent.database import User, init_db
from agent.luma import LumaClient
from agent.memory import MemoryClient
from agent.registration import RegistrationService

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
registration_service = RegistrationService()

# Register auth routes
app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Registration request/response schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    event_url: str
    custom_field_answers: dict[str, str] | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/register")
async def register_for_event(
    body: RegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """Register the authenticated user for a Luma event via Playwright."""
    # Check Luma credentials
    if not current_user.luma_email or not current_user.luma_password_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Luma credentials not configured",
        )

    # Decrypt luma_password
    luma_password = decrypt_luma_password(current_user.luma_password_encrypted)

    # Build profile data dict
    profile_data = {
        "name": current_user.name,
        "email": current_user.email,
        "linkedin_url": current_user.linkedin_url,
        "job_title": current_user.job_title,
        "company": current_user.company,
        "phone": current_user.phone,
        "twitter_x": current_user.twitter_x,
        "luma_email": current_user.luma_email,
        "luma_password": luma_password,
    }

    result = await registration_service.register_for_event(
        user_id=str(current_user.id),
        event_url=body.event_url,
        profile_data=profile_data,
        custom_field_answers=body.custom_field_answers,
    )

    return result.model_dump()


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
