# Environment

Environment variables, external dependencies, and setup notes.

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Required Environment Variables

| Variable | Used By | Required | Notes |
|---|---|---|---|
| LIVEKIT_URL | main.py | Yes | LiveKit Cloud server URL |
| LIVEKIT_API_KEY | main.py | Yes | LiveKit API key for token generation |
| LIVEKIT_API_SECRET | main.py | Yes | LiveKit API secret |
| OPENAI_API_KEY | voice_agent.py | Yes | For GPT-4o-mini LLM and TTS |
| DEEPGRAM_API_KEY | voice_agent.py | Yes | For speech-to-text |
| APIFY_API_TOKEN | luma.py | Yes | For event scraping via Apify |
| JWT_SECRET_KEY | main.py | Yes (NEW) | Secret key for JWT token signing |
| LUMA_EVENT_CATEGORIES | luma.py | No | Default: "ai,tech" |
| LUMA_CITIES | luma.py | No | Default: "San Francisco" |
| MEM0_API_KEY | memory.py | No | Optional mem0 integration |
| NEXT_PUBLIC_API_URL | frontend | No | Default: "http://localhost:8000" |

## Platform Notes

- **OS**: Windows 10/11, PowerShell
- **Python**: 3.13 in venv at `C:\Users\shivo\Projects\luma-agent\venv`
- **Node**: v20.20.1, npm 10.8.2
- **Shell**: Use PowerShell syntax (`;` not `&&` for chaining)
- **Playwright**: Requires `playwright install chromium` after pip install

## Encryption

- User passwords: bcrypt hashing
- Luma passwords: Fernet symmetric encryption (key derived from JWT_SECRET_KEY or separate ENCRYPTION_KEY)
- JWT tokens: python-jose with HS256 algorithm
