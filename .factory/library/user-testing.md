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
