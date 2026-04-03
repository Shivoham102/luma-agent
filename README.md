# Luma Voice Agent

A voice-first AI agent that discovers and registers you for Luma events — entirely hands-free. Speak to find events matching your interests, hear a curated list read back to you, and register with a single voice command. Preferences are remembered across sessions via mem0.

---

## What it does

1. Greets you via ElevenLabs voice
2. Captures your email by voice and links your Luma account
3. Fetches upcoming Luma events filtered by your stored preferences (mem0)
4. Reads out a short list of relevant events with one-line descriptions
5. Lets you register for any event by saying its name or number
6. Checks your existing Luma calendar for scheduling conflicts before registering
7. Confirms the registration by voice, then updates your preference memory for next time

---

## Architecture overview

```
User voice
    │
    ▼
ElevenLabs Conversational AI  ──►  STT + TTS (real-time)
    │
    ▼
Agent (Python / FastAPI)
    ├── Luma API          → fetch events, check registrations, register
    ├── mem0              → read/write user preferences across sessions
    └── ElevenLabs SDK    → stream voice responses
```

---

## Tech stack

| Layer | Tool | Notes |
|---|---|---|
| Voice | ElevenLabs Conversational AI | STT + TTS in one SDK |
| Agent backend | Python + FastAPI | handles webhooks from ElevenLabs |
| Event data | Luma API | `/event/list`, `/event/register` |
| Memory | mem0 | cloud-hosted, per-user preference storage |
| Email normalization | custom util | parses spoken emails ("at" → `@`) |

---

## Prerequisites

- Python 3.11+
- A [Luma API key](https://lu.ma/developers) (server-side key, not per-user OAuth)
- An [ElevenLabs](https://elevenlabs.io) account with Conversational AI enabled
- A [mem0](https://app.mem0.ai) account and API key
- `ngrok` or equivalent for local webhook tunneling during development

---

## Project structure

```
luma-voice-agent/
├── main.py                  # FastAPI app, ElevenLabs webhook handler
├── agent/
│   ├── conversation.py      # Turn logic, intent parsing, state machine
│   ├── luma.py              # Luma API wrapper (fetch, register, conflict check)
│   ├── memory.py            # mem0 read/write helpers
│   └── email_parser.py      # Normalizes spoken email strings
├── prompts/
│   └── system_prompt.txt    # ElevenLabs agent system prompt
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/your-username/luma-voice-agent.git
cd luma-voice-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_agent_id          # created in ElevenLabs dashboard
LUMA_API_KEY=your_luma_api_key
MEM0_API_KEY=your_mem0_api_key
```

### 3. Set up your ElevenLabs agent

1. Go to [elevenlabs.io](https://elevenlabs.io) → **Conversational AI** → **Create Agent**
2. Paste the contents of `prompts/system_prompt.txt` as the system prompt
3. Set the **webhook URL** to `https://your-tunnel-url/webhook` (see step 5)
4. Copy the **Agent ID** into your `.env`

The system prompt instructs the agent to:
- Welcome the user with one sentence
- Ask for their email and read it back for confirmation
- Use tool calls to fetch events, check conflicts, and register

### 4. Configure mem0

Log into [app.mem0.ai](https://app.mem0.ai) and copy your API key into `.env`. mem0 will automatically create a memory namespace per user ID (derived from their email). No additional setup is required — the agent writes preference signals after each registration automatically.

What gets stored in mem0:
- Event categories the user registers for (e.g., "AI", "Web3", "Design")
- Preferred times (weekday evening, weekend morning)
- Hosts or communities the user has attended before
- Any explicit preferences stated in conversation ("I prefer free events")

### 5. Run the server locally

```bash
# Terminal 1: start the FastAPI server
uvicorn main:app --reload --port 8000

# Terminal 2: expose it via ngrok
ngrok http 8000
```

Copy the ngrok HTTPS URL and paste it into your ElevenLabs agent webhook settings as `https://<ngrok-url>/webhook`.

### 6. Test the flow

Open the ElevenLabs agent test interface or call it directly. The expected conversation:

```
Agent:  "Hey! I'm your Luma event assistant. What's your email address?"
User:   "shivoham at gmail dot com"
Agent:  "Got it — shivoham@gmail.com. Is that right?"
User:   "Yes"
Agent:  "Found your Luma account. Pulling up events for you..."
Agent:  "Here are 3 events coming up this week based on your interests:
          1. AGI House Founders Dinner — Tuesday 7pm, networking + demos
          2. AI Safety Reading Group — Wednesday 6pm, paper discussion
          3. SF DeFi Builders Meetup — Friday 8pm, open building session
         Which one would you like to join?"
User:   "Register me for the first one"
Agent:  "You're already free that evening. Signing you up for AGI House
         Founders Dinner on Tuesday at 7pm — shall I confirm?"
User:   "Yes"
Agent:  "Done! You're registered. See you Tuesday."
```

---

## Key implementation notes for AI coding tools

When building this with Cursor, Claude Code, or Windsurf, give the tool this context upfront:

**Email parsing** — spoken emails need normalization before any API call. The util in `agent/email_parser.py` should handle: "at" → `@`, "dot" → `.`, "underscore" → `_`, "dash" → `-`, and strip spaces. Always read the parsed email back to the user and wait for explicit confirmation before proceeding.

**State machine** — the conversation has distinct states: `AWAIT_EMAIL`, `AWAIT_EMAIL_CONFIRM`, `AWAIT_PICK`, `AWAIT_CONFIRM`, `DONE`. Track state per session ID (ElevenLabs provides a `conversation_id`). Do not rely on the LLM to remember state across turns — store it server-side in a dict or Redis.

**Conflict check** — call `GET /user/calendar` with the user's email to get their existing Luma registrations, then compare event start/end times before registering. If there's an overlap, warn the user but offer to register anyway (they may want both).

**mem0 writes** — after a successful registration, extract signals from the event metadata and write them as natural language memories:

```python
mem0_client.add(
    messages=[{"role": "user", "content": f"I registered for {event_name}, a {category} event on {date}"}],
    user_id=user_email
)
```

**mem0 reads** — at the event-fetch step, retrieve the user's memories and inject them into the Luma API filter or into the LLM prompt to rank/filter results:

```python
memories = mem0_client.search(query="what events does this user like", user_id=user_email)
```

**ElevenLabs tool calls** — define `fetch_events`, `check_conflict`, and `register_event` as tools in your ElevenLabs agent config. The agent will call these via webhook; your FastAPI server handles each and returns structured JSON responses.

**Never register without confirmation** — always read the event name, date, and time back to the user and require an explicit "yes" before calling the registration endpoint.

---

## requirements.txt

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
elevenlabs>=1.2.0
mem0ai>=0.1.0
httpx>=0.27.0
python-dotenv>=1.0.0
pydantic>=2.7.0
```

---

## Environment variable reference

| Variable | Where to get it |
|---|---|
| `ELEVENLABS_API_KEY` | elevenlabs.io → Profile → API Keys |
| `ELEVENLABS_AGENT_ID` | ElevenLabs → Conversational AI → your agent |
| `LUMA_API_KEY` | lu.ma → Settings → Developers |
| `MEM0_API_KEY` | app.mem0.ai → API Keys |

---

## Extending this project

- **Broader event discovery** — swap the Luma API fetch for an Apify actor to scrape public Luma event pages beyond the user's own calendar. Useful for discovering events from orgs the user doesn't follow yet.
- **Richer preference signals** — after the session, run a post-processing step that extracts implicit signals (events the user skipped, time of day they tend to ask, topics mentioned in passing) and writes them to mem0.
- **Multi-event registration** — extend the pick intent parser to handle "register me for 1 and 3" in one turn.
- **Web UI companion** — show a minimal card UI alongside the voice agent so users can see the event list rendered visually while hearing it read aloud.

