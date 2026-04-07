#!/bin/bash
# Environment setup - idempotent

# Install Python dependencies
if [ -f "venv/Scripts/pip.exe" ]; then
    venv/Scripts/pip.exe install -r requirements.txt -q
elif [ -f "venv/bin/pip" ]; then
    venv/bin/pip install -r requirements.txt -q
fi

# Install frontend dependencies
cd frontend && npm install --silent && cd ..
