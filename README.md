# Lumi — AI Voice Assistant for Luma Event Discovery

Lumi is a voice-first AI assistant that helps you discover and register for [Luma](https://lu.ma) events — entirely hands-free. Speak to find events matching your interests, hear a curated list read back to you, and register with a single voice command.

---

## Architecture Overview

Lumi runs as three separate processes:

```
User speaks
    │
    ▼
Next.js Frontend (LiveKit client)
    │  WebRTC audio
    ▼
LiveKit Cloud
    │
    ▼
Voice Agent (LiveKit Agents framework)
    ├── Deepgram STT       → speech-to-text
    ├── Silero VAD         → voice activity detection
    ├── OpenAI GPT-4o-mini → LLM for conversation
    ├── OpenAI TTS         → text-to-speech
    ├── LumaClient         → Apify actor for event data
    └── mem0               → user preference memory
    │
    ▼  (LiveKit data channel)
Frontend sidebar renders events
```

| Layer | Technology | Purpose |
|---|---|---|
| Voice pipeline | [LiveKit Agents](https://docs.livekit.io/agents/) | Real-time STT → LLM → TTS orchestration |
| Speech-to-text | [Deepgram](https://deepgram.com/) | Transcribes user speech |
| Voice activity | [Silero VAD](https://github.com/snakers4/silero-vad) | Detects when the user is speaking |
| LLM | OpenAI GPT-4o-mini | Conversational reasoning and tool calls |
| Text-to-speech | OpenAI TTS | Generates voice responses |
| Event data | [Apify](https://apify.com/) (`matyascimbulka/luma-event-scraper`) | Scrapes public Luma events by category and city |
| Memory | [mem0](https://mem0.ai/) | Stores per-user preference signals across sessions |
| Backend | FastAPI | Generates LiveKit access tokens for the frontend |
| Frontend | Next.js + `livekit-client` | Orb UI, event sidebar, email modal |

---

## Project Structure

```
luma-agent/
├── main.py                     # FastAPI server (LiveKit token generation)
├── agent/
│   ├── voice_agent.py          # LiveKit voice agent (LumiAgent class, tools)
│   ├── luma.py                 # LumaClient — Apify actor wrapper for events
│   ├── conversation.py         # Conversation state placeholder
│   └── memory.py               # mem0 wrapper for user preferences
├── prompts/
│   └── system_prompt.txt       # LLM system instructions for the voice agent
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Main page: orb, LiveKit room, event rendering
│   │   │   ├── layout.tsx      # Root layout
│   │   │   └── globals.css     # Global styles (Tailwind)
│   │   ├── components/
│   │   │   ├── EventList.tsx   # Event sidebar list
│   │   │   ├── VoiceAgent.tsx  # Voice agent UI component
│   │   │   ├── CalendarView.tsx
│   │   │   ├── ConversationPanel.tsx
│   │   │   └── RegistrationModal.tsx
│   │   └── lib/
│   │       └── api.ts          # API client (token fetch)
│   └── package.json
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
└── README.md
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A [LiveKit Cloud](https://cloud.livekit.io/) project (or self-hosted LiveKit server)
- An [OpenAI](https://platform.openai.com/) API key
- A [Deepgram](https://deepgram.com/) API key
- An [Apify](https://apify.com/) API token
- (Optional) A [mem0](https://app.mem0.ai/) API key for cross-session preference memory

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description |
|---|---|
| `LIVEKIT_URL` | Your LiveKit server URL (e.g., `wss://your-project.livekit.cloud`) |
| `LIVEKIT_API_KEY` | LiveKit API key from your project dashboard |
| `LIVEKIT_API_SECRET` | LiveKit API secret from your project dashboard |
| `OPENAI_API_KEY` | OpenAI API key — used for GPT-4o-mini (LLM) and TTS |
| `DEEPGRAM_API_KEY` | Deepgram API key — used for speech-to-text |
| `APIFY_API_TOKEN` | Apify API token — used to run the Luma event scraper actor |
| `LUMA_EVENT_CATEGORIES` | Comma-separated event categories to search (e.g., `ai,tech,crypto`) |
| `LUMA_CITIES` | Comma-separated city names to search (e.g., `San Francisco,New York`) |
| `MEM0_API_KEY` | (Optional) mem0 API key for user preference memory |

---

## Setup

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/your-username/luma-agent.git
cd luma-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all required values (see [Environment Variables](#environment-variables) above).

---

## Running

You need **three separate terminals**:

### Terminal 1 — FastAPI backend (token server)

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Terminal 2 — Voice agent

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate
python agent/voice_agent.py start
```

### Terminal 3 — Next.js frontend

```bash
cd frontend
npm run dev
```

---

## Usage

1. Open [http://localhost:3000](http://localhost:3000) in your browser
2. Click the **orb** to start a voice session
3. Lumi will greet you and ask for your email (entered via a modal)
4. After submitting your email, Lumi fetches upcoming events and reads them to you
5. Pick an event by name or number — Lumi checks for conflicts and confirms
6. Confirm registration and Lumi provides the event link in the sidebar

---

## How It Works

1. The **frontend** requests a LiveKit access token from the FastAPI backend (`POST /token`)
2. The frontend connects to the **LiveKit Cloud** room using the token
3. The **voice agent** joins the same room and begins the conversation
4. User speech is transcribed by **Deepgram STT**, processed by **GPT-4o-mini**, and responses are spoken via **OpenAI TTS**
5. The agent uses **function tools** to fetch events (via **Apify**), check conflicts, and trigger registration
6. Event data is sent to the frontend via **LiveKit data channels** and rendered in the sidebar
