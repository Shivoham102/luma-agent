import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import openai, deepgram, silero
from agent.luma import LumaClient

load_dotenv()
logger = logging.getLogger("luma-voice-agent")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.txt"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

luma_client = LumaClient()

# Maps room_name → JWT token received from the frontend via data channel
user_tokens: dict[str, str] = {}


@function_tool()
async def fetch_events(context: RunContext, city: str) -> str:
    """Fetch upcoming Luma events for a specific city.

    Args:
        city: The city to search for events in (e.g. 'San Francisco', 'New York').
    """
    events = await luma_client.list_events(city=city)
    room = context.session.room_io.room
    if room:
        await room.local_participant.publish_data(
            json.dumps({"type": "events", "data": events}).encode(),
            topic="ui_update",
        )
    if not events:
        return json.dumps({"message": "No upcoming events found."})
    return json.dumps(events)


@function_tool()
async def check_conflict(context: RunContext, event_id: str) -> str:
    """Check if the user has a scheduling conflict for a given event."""
    event = await luma_client.get_event(event_id)
    if not event:
        return json.dumps({"error": "Event not found"})
    return json.dumps({"has_conflict": False, "event": event})


@function_tool()
async def register_event(context: RunContext, event_url: str) -> str:
    """Register the user for a Luma event using the backend registration service.

    Args:
        event_url: The lu.ma event URL to register for.
    """
    room = context.session.room_io.room
    room_name = room.name if room else None
    token = user_tokens.get(room_name) if room_name else None

    if not token:
        if room:
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "registration_progress",
                    "data": {"event_url": event_url, "status": "failed", "error": "No authentication token available"},
                }).encode(),
                topic="ui_update",
            )
        return json.dumps({
            "success": False,
            "error": "No authentication token available. The user may need to re-login.",
        })

    # Send progress update to frontend
    if room:
        await room.local_participant.publish_data(
            json.dumps({
                "type": "registration_progress",
                "data": {"event_url": event_url, "status": "registering"},
            }).encode(),
            topic="ui_update",
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{API_BASE_URL}/api/register",
                json={"event_url": event_url},
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code == 401:
            if room:
                await room.local_participant.publish_data(
                    json.dumps({
                        "type": "registration_progress",
                        "data": {"event_url": event_url, "status": "failed", "error": "Authentication expired"},
                    }).encode(),
                    topic="ui_update",
                )
            return json.dumps({
                "success": False,
                "error": "Authentication expired. The user needs to re-login.",
            })

        if resp.status_code == 400:
            error_detail = resp.json().get("detail", "Bad request")
            if room:
                await room.local_participant.publish_data(
                    json.dumps({
                        "type": "registration_progress",
                        "data": {"event_url": event_url, "status": "failed", "error": error_detail},
                    }).encode(),
                    topic="ui_update",
                )
            return json.dumps({
                "success": False,
                "error": error_detail,
            })

        if resp.status_code != 200:
            error_msg = f"Registration failed with status {resp.status_code}"
            if room:
                await room.local_participant.publish_data(
                    json.dumps({
                        "type": "registration_progress",
                        "data": {"event_url": event_url, "status": "failed", "error": error_msg},
                    }).encode(),
                    topic="ui_update",
                )
            return json.dumps({
                "success": False,
                "error": error_msg,
            })

        result = resp.json()

        # If unknown fields are present, return them so the LLM can ask the user
        if result.get("status") == "needs_input" and result.get("unknown_fields"):
            if room:
                await room.local_participant.publish_data(
                    json.dumps({
                        "type": "registration_progress",
                        "data": {"event_url": event_url, "status": "needs_input"},
                    }).encode(),
                    topic="ui_update",
                )
            return json.dumps({
                "success": False,
                "needs_input": True,
                "unknown_fields": result["unknown_fields"],
                "message": "The event has custom fields that need answers before registration can proceed.",
            })

        # Determine final status for frontend
        reg_status = "registered" if result.get("status") == "registered" else "failed"
        if result.get("status") in ("pending_approval", "already_registered"):
            reg_status = "registered"

        # Send final result to frontend via data channel
        if room:
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "registration_progress",
                    "data": {
                        "event_url": event_url,
                        "status": reg_status,
                        "error": result.get("error"),
                    },
                }).encode(),
                topic="ui_update",
            )

        return json.dumps({
            "success": result.get("status") in ("registered", "pending_approval", "already_registered"),
            "status": result.get("status"),
            "event_name": result.get("event_name", ""),
            "message": result.get("message", ""),
        })

    except httpx.TimeoutException:
        if room:
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "registration_progress",
                    "data": {"event_url": event_url, "status": "failed", "error": "Timeout"},
                }).encode(),
                topic="ui_update",
            )
        return json.dumps({
            "success": False,
            "error": "Registration request timed out. Please try again.",
        })
    except Exception as exc:
        logger.error("register_event error: %s", exc)
        if room:
            await room.local_participant.publish_data(
                json.dumps({
                    "type": "registration_progress",
                    "data": {"event_url": event_url, "status": "failed", "error": str(exc)},
                }).encode(),
                topic="ui_update",
            )
        return json.dumps({
            "success": False,
            "error": f"Registration failed: {exc}",
        })


class LumiAgent(Agent):
    def __init__(self) -> None:
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(),
            tools=[fetch_events, check_conflict, register_event],
        )

    async def on_enter(self):
        await self.session.generate_reply(
            instructions="Say exactly: 'Hi! I'm Lumi, your event assistant. What city would you like to see events in?' Do NOT call any tools.",
            allow_interruptions=False,
        )


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.5,
        max_endpointing_delay=5.0,
    )

    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        if data.participant and data.participant.identity == participant.identity:
            try:
                msg = json.loads(data.data.decode())
                if msg.get("type") == "auth_token":
                    token = msg.get("token", "")
                    if token:
                        user_tokens[ctx.room.name] = token
                        logger.info("Stored auth token for room %s", ctx.room.name)
            except Exception as e:
                logger.error(f"Error processing data from user: {e}")

    await session.start(
        room=ctx.room,
        agent=LumiAgent(),
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
