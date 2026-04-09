# Architecture

## System Overview

Luma Agent is a voice-powered event discovery and registration assistant. Users interact via voice (WebRTC audio) and a web UI to browse Luma events and get automatically registered.

## Components

### FastAPI Backend (`main.py`)
- HTTP API server on port 8000
- Endpoints: `/health`, `/token` (LiveKit token generation), `/auth/*` (signup/login/me), `/api/register` (Playwright registration)
- SQLite database via SQLAlchemy for user profiles
- JWT-based authentication (24h expiry, bcrypt password hashing)
- CORS enabled for frontend origin

### Voice Agent (`agent/voice_agent.py`)
- LiveKit Agents framework — runs as a separate process connecting to LiveKit Cloud
- Pipeline: Deepgram STT → OpenAI GPT-4o-mini LLM → OpenAI TTS
- Function tools: `request_user_email`, `fetch_events`, `check_conflict`, `register_event`
- Communicates with frontend via LiveKit data channel (JSON messages)
- Topic `ui_update` for agent→frontend, `user_input` for frontend→agent

### Luma Client (`agent/luma.py`)
- Wraps Apify actor for event scraping
- Returns normalized event objects: id, name, description, start_time, end_time, location, url, cover_url

### Registration Engine (`agent/registration.py` — NEW)
- Playwright async API for headless Chromium automation
- Logs into Luma with user's stored credentials (email + password)
- Caches session via Playwright storageState in `playwright_sessions/` directory
- Detects form fields, maps profile data to form, submits registration
- Reports unknown custom fields back for voice agent to ask user
- Handles edge cases: paid events, approval-required, already registered

### Next.js Frontend (`frontend/`)
- Next.js 16 with App Router, React 19, Tailwind CSS v4
- Routes: `/login`, `/signup`, `/` (protected main app)
- Main app: orb UI for voice interaction, event sidebar, email modal
- LiveKit client for WebRTC audio + data channel
- JWT stored in localStorage for API authentication

## Data Flows

### Authentication Flow
1. User visits `/signup` → fills form → POST /auth/signup → user created in SQLite → redirect to /login
2. User visits `/login` → enters credentials → POST /auth/login → JWT returned → stored in localStorage → redirect to /
3. Protected routes check localStorage for JWT → redirect to /login if missing

### Event Registration Flow
1. Voice agent sends events to frontend via data channel
2. User requests registration via voice
3. Agent calls `register_event` tool → hits POST /api/register
4. Backend loads user profile from DB, starts Playwright
5. Playwright: check cached session → login if needed → navigate to event → fill form → submit
6. If custom fields detected → return to agent → agent asks user via voice → retry with answers
7. Result sent back to frontend via data channel → sidebar updated

### Data Channel Message Types
- `request_email` — agent→frontend: show email modal
- `email` — frontend→agent: user's email address
- `events` — agent→frontend: list of events
- `registration` — agent→frontend: registration result
- `registration_progress` — agent→frontend: progress updates (registering/registered/failed)

## Database Schema (SQLite)

### users table
- id (INTEGER PRIMARY KEY)
- name (TEXT NOT NULL)
- email (TEXT UNIQUE NOT NULL)
- password_hash (TEXT NOT NULL) — bcrypt
- linkedin_url (TEXT)
- job_title (TEXT)
- company (TEXT)
- phone (TEXT)
- twitter_x (TEXT)
- luma_email (TEXT)
- luma_password_encrypted (TEXT) — encrypted with Fernet
- created_at (DATETIME)

## Key Invariants
- User passwords are NEVER stored in plaintext (bcrypt hash)
- Luma passwords are NEVER stored in plaintext (Fernet encryption)
- JWT tokens expire after 24 hours
- Playwright always runs headless, browser context always cleaned up (finally block)
- Registration endpoint requires valid JWT
- /token endpoint requires valid JWT (after auth is added)
