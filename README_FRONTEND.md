# TruthLens Frontend

## Quick Start

### 1. Activate Python Virtual Environment

```bash
cd /Users/sashya/Documents/All-Projects/TruthLens
source .venv/bin/activate
```

### 2. Start the Backend Server

```bash
python -m uvicorn truthlens.backend.app.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`.

> **Note:** If `GEMINI_API_KEY` is not set, the backend will use a mock generator for responses.

### 3. Open the UI

Open your browser and navigate to:

- **Main demo:** `http://localhost:8000/index.html`
- **Alternative demo:** `http://localhost:8000/demo.html`

## What's Inside

- **`public/index.html`** — Minimal single-page UI with vanilla JS
  - POSTs to `/query` endpoint with question and k parameter
  - Displays JSON response
  - Includes error handling and console logging
  
- **`public/demo.html`** — Alternative demo page with styled UI

## API Contract

The frontend calls the backend `/query` endpoint:

```
POST /query
Content-Type: application/json

{
  "question": "Who discovered penicillin?",
  "k": 3
}
```

Response (JSON):
```json
{
  "answer": "...",
  "sources": [...],
  "confidence": 0.95
}
```

See `truthlens/backend/api_contract.md` for full backend API details.

## Development Notes

- No build tool or npm dependencies required
- Pure vanilla JavaScript (ES6+)
- Uses Fetch API for HTTP requests
- All styling is inline CSS

## Testing

Test the API with curl:

```bash
curl -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"Who discovered penicillin?","k":3}'
```

Or use the convenience npm script (if npm is installed):

```bash
npm run test:curl
```
