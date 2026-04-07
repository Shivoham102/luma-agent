# User Testing

## Validation Surface

The primary testing surface is the voice agent interaction through the web browser at http://localhost:3000. Testing requires:
- A running FastAPI backend (port 8000)
- A running LiveKit voice agent process
- A running Next.js frontend (port 3000)
- Valid API keys for LiveKit, OpenAI, Deepgram, and Apify

Voice/audio testing cannot be automated -- requires manual user interaction (pressing the orb, listening to the agent, observing UI changes).

## Validation Concurrency

Max concurrent validators: 1 (voice interaction is inherently serial and requires human observation)

## Testing Approach

All validation is manual per user preference. No automated tests.

## Flow Validator Guidance: browser-voice-flow

- Isolation boundary: use only the shared local app endpoints (`http://localhost:3000` frontend, `http://localhost:8000` backend) and the already-running local voice agent process.
- Do not change application code, environment variables, or service ports while validating.
- Do not run parallel voice sessions; only one orb/session at a time.
- Keep evidence under the assigned evidence directory (screenshots, step notes, observed behavior).

## Flow Validator Guidance: code-review

- Isolation boundary: read-only inspection of repository files relevant to assigned assertions.
- Do not modify files, dependencies, or runtime services during code-review validation.
- Record exact file paths and snippets that support each assertion outcome.
