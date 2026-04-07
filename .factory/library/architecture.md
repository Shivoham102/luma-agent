# Architecture

## System Overview

Luma Agent is a voice-powered event assistant with three processes:

1. **FastAPI Backend** (`main.py`, port 8000) -- Generates LiveKit access tokens via `POST /token`
2. **LiveKit Voice Agent** (`agent/voice_agent.py`, separate process) -- Joins LiveKit rooms as an AI agent with STT/LLM/TTS pipeline
3. **Next.js Frontend** (`frontend/`, port 3000) -- Orb UI for voice interaction, event sidebar, email modal

## Data Flow

```
User speaks -> LiveKit WebRTC -> Deepgram STT -> OpenAI GPT-4o-mini -> OpenAI TTS -> LiveKit WebRTC -> User hears
                                                      |
                                              (function tools)
                                                      |
                                              LumaClient (Apify) -> Events sent via data channel -> Frontend sidebar
```

## Key Components

- `agent/luma.py` -- LumaClient: fetches events from Apify, normalizes output format
- `agent/voice_agent.py` -- LumiAgent class with tools (request_user_email, fetch_events, check_conflict, register_event)
- `frontend/src/app/page.tsx` -- Main page with orb, LiveKit room connection, event rendering
- `prompts/system_prompt.txt` -- LLM system instructions for the voice agent

## Event Data Normalization

LumaClient.list_events() returns normalized dicts: `{id, name, description, start_time, end_time, location, url, cover_url}`
The frontend expects this exact format. Any backend changes must preserve this interface.
