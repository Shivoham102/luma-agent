---
name: fullstack-worker
description: Implements backend Python and frontend React/Next.js changes for the Luma voice agent project
---

# Fullstack Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Features involving Python backend code (`agent/`, `main.py`, `requirements.txt`), frontend code (`frontend/src/`), database models, API endpoints, Next.js pages/components, and Playwright automation code.

## Required Skills

- `agent-browser` — MUST be invoked for features that add or modify UI (pages, components, modals). Use it to verify rendered output matches expectations after implementation.

## Work Procedure

1. **Read the feature description and preconditions.** Understand the full scope. Read `AGENTS.md` for constraints. Read `.factory/library/architecture.md` for system design. Read `.factory/library/environment.md` for env var details.

2. **Read ALL files you will modify** and any files they import/depend on. Understand existing patterns before writing code. For frontend work, also read `frontend/src/app/globals.css` and `frontend/src/app/layout.tsx` to match styling.

3. **Write tests FIRST (TDD).** For Python features:
   - Create test file in project root or `tests/` directory (e.g., `tests/test_auth.py`)
   - Write failing tests covering expected behavior from the feature's `expectedBehavior`
   - Run tests to confirm they fail: `C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -m pytest tests/ -v --tb=short -x`

4. **Implement the changes.** Make focused edits following existing patterns:
   - Python: async/await, type hints, Pydantic models, SQLAlchemy 2.0
   - Frontend: React 19 hooks, Tailwind CSS v4 utilities, Next.js App Router
   - Match the dark theme: bg `#0a0a0a`, foreground `#ededed`
   - NEVER log or return passwords/tokens in plaintext
   - Always use `playwright.async_api` (not sync_api)
   - Clean up Playwright browser contexts in `finally` blocks

5. **Run tests to confirm they pass.**
   - Python: `C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -m pytest tests/ -v --tb=short -x`
   - Frontend typecheck: `cd C:\Users\shivo\Projects\luma-agent\frontend; npx tsc --noEmit`
   - Frontend lint: `cd C:\Users\shivo\Projects\luma-agent\frontend; npm run lint`

6. **Verify UI changes with agent-browser.** For any feature that adds or modifies UI:
   - Start backend: `Start-Process -NoNewWindow -FilePath "C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","main:app","--port","8000","--reload" -WorkingDirectory "C:\Users\shivo\Projects\luma-agent"`
   - Start frontend: `Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory "C:\Users\shivo\Projects\luma-agent\frontend"`
   - Wait for both to be ready (healthcheck port 8000 and 3000)
   - Invoke `agent-browser` skill to navigate and verify the UI
   - Record each check in `interactiveChecks`
   - Stop services when done

7. **Verify no import/syntax errors.** Run quick import checks for modified Python modules:
   `C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -c "import main; print('ok')"`

8. **Commit your changes** with a clear, descriptive commit message.

## Example Handoff

```json
{
  "salientSummary": "Implemented /auth/signup and /auth/login endpoints with SQLite user model, bcrypt password hashing, and JWT token generation. Wrote 8 pytest tests covering signup validation, duplicate email, login success/failure, and token expiry. All tests pass. Verified via curl that signup returns user data without password and login returns JWT.",
  "whatWasImplemented": "Created agent/auth.py with User SQLAlchemy model, signup/login Pydantic schemas, bcrypt hashing, JWT creation (24h expiry). Added /auth/signup, /auth/login, /auth/me endpoints to main.py via APIRouter. Created tests/test_auth.py with 8 test cases. Updated requirements.txt with bcrypt and python-jose[cryptography].",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "venv\\Scripts\\python.exe -m pytest tests/test_auth.py -v --tb=short",
        "exitCode": 0,
        "observation": "8 tests passed: test_signup_success, test_signup_duplicate_email, test_signup_missing_name, test_login_success, test_login_wrong_password, test_login_nonexistent_email, test_me_valid_token, test_me_no_token"
      },
      {
        "command": "curl -X POST http://localhost:8000/auth/signup -H \"Content-Type: application/json\" -d \"{\\\"name\\\":\\\"Test\\\",\\\"email\\\":\\\"test@test.com\\\",\\\"password\\\":\\\"SecurePass1!\\\"}\"",
        "exitCode": 0,
        "observation": "Returns {id: 1, name: 'Test', email: 'test@test.com'} — no password in response"
      }
    ],
    "interactiveChecks": [
      {
        "action": "Navigated to http://localhost:3000/signup via agent-browser",
        "observed": "Signup form rendered with all 10 fields (name, email, password, LinkedIn, job title, company, phone, Twitter/X, Luma email, Luma password). Dark theme matches existing app. Submit button visible."
      },
      {
        "action": "Filled signup form with valid data and clicked Submit",
        "observed": "Form submitted successfully, redirected to /login page. No console errors."
      }
    ]
  },
  "tests": {
    "added": [
      {
        "file": "tests/test_auth.py",
        "cases": [
          { "name": "test_signup_success", "verifies": "POST /auth/signup creates user and returns data without password" },
          { "name": "test_signup_duplicate_email", "verifies": "Duplicate email returns 409" },
          { "name": "test_login_success", "verifies": "Valid credentials return JWT token" },
          { "name": "test_login_wrong_password", "verifies": "Wrong password returns 401" }
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- A required environment variable is missing and cannot be set
- Existing code has unexpected dependencies conflicting with the feature
- Tests reveal bugs in existing code unrelated to the current feature
- Playwright browser automation fails due to Luma site changes (new form structure, CAPTCHA)
- Frontend build errors caused by incompatible dependency versions
- Database schema conflicts with existing data
