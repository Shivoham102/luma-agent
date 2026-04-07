# Environment

## Required Environment Variables

| Variable | Used By | Purpose |
|---|---|---|
| `LIVEKIT_URL` | main.py | LiveKit Cloud WebSocket URL |
| `LIVEKIT_API_KEY` | main.py | LiveKit auth for token generation |
| `LIVEKIT_API_SECRET` | main.py | LiveKit auth for token generation |
| `OPENAI_API_KEY` | voice_agent.py (via livekit-plugins-openai) | LLM (GPT-4o-mini) + TTS |
| `DEEPGRAM_API_KEY` | voice_agent.py (via livekit-plugins-deepgram) | STT |
| `APIFY_API_TOKEN` | agent/luma.py | Apify actor authentication |
| `LUMA_EVENT_CATEGORIES` | agent/luma.py | Comma-separated event categories (ai,tech,crypto) |
| `LUMA_CITIES` | agent/luma.py | Comma-separated city names (San Francisco,New York) |

## Python Virtual Environment

Located at `./venv`. Activate with `.\venv\Scripts\activate` (Windows).

## Dependencies

- Python: see `requirements.txt`
- Node.js: see `frontend/package.json`
