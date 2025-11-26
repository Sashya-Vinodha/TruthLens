# Setup & Run (Development)

## Prereqs
- Docker (recommended) OR Python 3.11 and git
- VS Code (optional)

## Using Docker (recommended)
1. docker-compose up --build
2. Open http://127.0.0.1:8000

## Local (no Docker)
1. python3 -m venv .venv
2. source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
3. pip install -r requirements.txt
4. bash scripts/run_dev.sh
5. Open http://127.0.0.1:8000

## Notes
- If `faiss-cpu` or other OS-specific packages fail on local install, use Docker.
- Copy `.env.example` to `truthlens/.env` and fill secrets if needed.
