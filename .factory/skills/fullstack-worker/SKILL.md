---
name: fullstack-worker
description: Implements backend Python and documentation changes for the Luma voice agent project
---

# Fullstack Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features that involve modifying Python backend code (`agent/`, `main.py`, `requirements.txt`), frontend code (`frontend/src/`), environment configuration (`.env.example`), or documentation (`README.md`).

## Required Skills

None.

## Work Procedure

1. **Read the feature description carefully.** Understand what files need to change and what the expected behavior is. Read `AGENTS.md` for constraints and architecture context.

2. **Read all files you will modify.** Before making any changes, read the current state of every file you plan to edit. Understand the existing patterns.

3. **Implement the changes.** Make focused, minimal edits. Follow existing code patterns (async/await, logging, error handling). For Python, preserve the existing module structure. For the LumaClient, ensure the output format matches what the frontend expects: `{id, name, description, start_time, end_time, location, url, cover_url}`.

4. **Verify no syntax errors.** Run `venv\Scripts\python.exe -c "import agent.luma; import agent.voice_agent; print('imports ok')"` (adjust for the files you changed). For frontend changes, run `cd frontend && npx tsc --noEmit`.

5. **Verify the changes make sense.** Re-read the modified files to confirm correctness. Check that:
   - No old code/references remain (e.g., old actor ID, old env var names)
   - Error handling is preserved
   - The data flow is intact

6. **Commit your changes** with a clear commit message describing what was changed and why.

## Example Handoff

```json
{
  "salientSummary": "Rewrote LumaClient to use matyascimbulka/luma-event-scraper via apify-client. Replaced LUMA_CALENDAR_SLUGS with LUMA_EVENT_CATEGORIES and LUMA_CITIES. Verified imports succeed and output format matches frontend expectations.",
  "whatWasImplemented": "Replaced the Apify actor in agent/luma.py from mhamas/luma-calendar-events-scraper (raw httpx) to matyascimbulka/luma-event-scraper (apify-client library). Updated .env.example with new env vars. Added apify-client to requirements.txt.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "venv\\Scripts\\python.exe -c \"from agent.luma import LumaClient; print('ok')\"",
        "exitCode": 0,
        "observation": "LumaClient imports successfully with apify-client"
      },
      {
        "command": "venv\\Scripts\\pip.exe install -r requirements.txt",
        "exitCode": 0,
        "observation": "All dependencies installed including apify-client"
      }
    ],
    "interactiveChecks": []
  },
  "tests": {
    "added": []
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- A required environment variable is missing and the code cannot be verified
- The existing code has unexpected dependencies or patterns that conflict with the feature requirements
- The frontend event data format has changed in ways that make backward compatibility impossible
