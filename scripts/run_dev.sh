#!/bin/bash
set -e
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
else
  echo "No .venv found. Create a venv first: python3 -m venv .venv && source .venv/bin/activate"
fi
echo "Starting dev server..."
uvicorn truthlens.backend.app.main:app --reload --port 8000
