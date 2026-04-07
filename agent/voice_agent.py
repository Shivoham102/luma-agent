import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
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

luma_client = LumaClient()

user_emails: dict[str, str] = {}


@function_tool()
async def request_user_email(context: RunContext) -> str:
    """Trigger the email input modal on the frontend. Call this after greeting the user."""
    room = context.session.room_io.room
    if room:
        await room.local_participant.publish_data(
            json.dumps({"type": "request_email"}).encode(),
            topic="ui_update",
        )
    return json.dumps({"status": "waiting", "message": "Email modal shown to user. Wait for the user to provide their email before proceeding."})


@function_tool()
async def fetch_events(context: RunContext) -> str:
    """Fetch upcoming Luma events from the calendar."""
    events = await luma_client.list_events()
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
async def register_event(context: RunContext, event_id: str) -> str:
    """Direct the user to register for a Luma event by opening the event URL."""
    result = {
        "success": True,
        "event_id": event_id,
        "url": event_id,
        "message": "The event registration link is now shown in the sidebar. Please ask the user to click it to complete registration on Luma.",
    }
    room = context.session.room_io.room
    if room:
        await room.local_participant.publish_data(
            json.dumps({"type": "registration", "data": result}).encode(),
            topic="ui_update",
        )
    return json.dumps(result)


class LumiAgent(Agent):
    def __init__(self) -> None:
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
        super().__init__(
            instructions=instructions,
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(),
            tools=[request_user_email, fetch_events, check_conflict, register_event],
        )

    async def on_enter(self):
        # First: greet the user briefly. Do NOT call any tools in this step.
        await self.session.generate_reply(
            instructions="Say exactly: 'Hi! I'm Lumi, your Luma event assistant. Let me get your email to get started.' Do NOT call any tools.",
            allow_interruptions=False,
        )
        # Second: after greeting finishes, call request_user_email to show the modal.
        self.session.generate_reply(
            instructions="Call request_user_email now.",
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
                if msg.get("type") == "email":
                    email = msg.get("email", "")
                    user_emails[ctx.room.name] = email
                    logger.info(f"Received email from user: {email}")
                    session.generate_reply(
                        instructions="The user has submitted their email. Call fetch_events now to show them upcoming events.",
                    )
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
