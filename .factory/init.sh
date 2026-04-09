#!/bin/bash
# Environment setup for luma-agent mission (idempotent)
# This runs on Windows via PowerShell, so commands use Windows paths

cd "C:\Users\shivo\Projects\luma-agent"

# Install Python dependencies
C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>/dev/null

# Install Playwright and Chromium browser
C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -m pip install playwright -q 2>/dev/null
C:\Users\shivo\Projects\luma-agent\venv\Scripts\python.exe -m playwright install chromium 2>/dev/null

# Install frontend dependencies
cd frontend && npm install --silent 2>/dev/null
cd ..

# Create playwright_sessions directory if it doesn't exist
mkdir -p playwright_sessions 2>/dev/null

# Create SQLite database directory marker
touch luma_agent.db 2>/dev/null

echo "Init complete"
