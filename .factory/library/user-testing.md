# User Testing

Testing surface, tools, and resource cost classification.

---

## Validation Surface

### Browser UI (Primary)
- **Surface**: Next.js frontend at http://localhost:3000
- **Tool**: agent-browser
- **What to test**: Signup/login pages, protected routes, event sidebar, registration status badges
- **Setup**: Frontend dev server must be running on port 3000, backend on port 8000
- **Auth flows**: Navigate to /signup, /login, verify redirects and form submissions

### API Endpoints (Secondary)
- **Surface**: FastAPI backend at http://localhost:8000
- **Tool**: curl
- **What to test**: /auth/signup, /auth/login, /auth/me, /api/register, /token, /health
- **Auth**: Most endpoints require JWT Bearer token in Authorization header
- **Windows note**: In PowerShell, use `curl.exe` explicitly (not `curl`) to avoid aliasing to `Invoke-WebRequest`

### Voice Agent (Out of Scope for Automated Testing)
- Voice interactions (STT/TTS) cannot be automated via agent-browser
- Data channel communication is tested indirectly via API and frontend state

## Validation Concurrency

### agent-browser
- Machine: 16GB RAM, 24 CPU cores, ~4GB free at baseline
- Each agent-browser instance: ~300MB RAM + frontend dev server ~470MB
- Usable headroom: ~4GB * 0.7 = 2.8GB
- **Max concurrent: 3** (conservative due to limited free RAM)
- Frontend dev server is shared across instances

### curl
- Negligible resource usage
- **Max concurrent: 5**

## Test Fixtures

- Registration engine tests require real Luma account credentials stored for a test user
- Event-specific tests (paid, approval-required, free) depend on finding real events of each type on lu.ma
- Validators should create test users via POST /auth/signup before testing auth-protected flows

## Flow Validator Guidance: agent-browser

- Scope: auth UI assertions (`VAL-AUTH-001` to `VAL-AUTH-015`, `VAL-AUTH-021`) on `http://localhost:3000`.
- Isolation boundary:
  - Use only local app URLs (`localhost:3000`, `localhost:8000`).
  - Use unique test emails per assertion group to avoid duplicate collisions.
  - Do not alter app configuration, env files, or shared infrastructure.
- Shared-state cautions:
  - Authenticated sessions (cookies/localStorage) are global per browser context; start from a fresh context for redirect checks.
  - Duplicate-email checks intentionally reuse one email in the same flow.
- Known environment caveat:
  - If `agent-browser` cannot start due the known daemon `htmlfy` module error documented in mission `AGENTS.md`, mark affected assertions as `blocked` with the exact blocker and collect any available logs.

## Flow Validator Guidance: curl

- Scope: auth API and DB-backed assertions (`VAL-AUTH-016` to `VAL-AUTH-020`, `VAL-AUTH-022` to `VAL-AUTH-024`) on `http://localhost:8000`.
- Isolation boundary:
  - Use unique test users (`+timestamp` emails) for signup/login checks.
  - Read only local SQLite files in this repo (`luma_agent.db`) when DB inspection is required.
  - Do not mutate unrelated tables or production-like external systems.
- Shared-state cautions:
  - Reuse one signed-in user only within the same assertion group; do not assume any pre-existing user records.
  - Token-expiry checks must use crafted expired JWTs, not clock changes.
