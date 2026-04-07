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
