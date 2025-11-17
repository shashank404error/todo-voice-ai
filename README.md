# Voice-Driven Smart Todo

A small end-to-end demo that turns spoken commands into structured todo actions. The browser streams microphone audio to a local WebSocket server. The server uses Azure Cognitive Services Speech to transcribe audio and Gemini to interpret intent into a structured JSON action, updates an in-memory todo list, and sends results back to the UI.

<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/38760033/515141531-646cbd90-5c83-4d1d-8f88-f3c14452505e.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAVCODYLSA53PQK4ZA%2F20251117%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20251117T114919Z&X-Amz-Expires=300&X-Amz-Signature=89a29e697482f1b9700f29897a8b6272be05c03ac8c2ada102051834d32f63a1&X-Amz-SignedHeaders=host" alt="Screenshot of the below operations" width="50%" height="600">

## Usage Examples
- "Buy milk at 6pm" → `create` with `title` and RFC3339 `scheduled_time`
- "Do I have to buy something today?" → `fetch` with `title="Buy milk at 6pm`
- "Will buy milk not today but tomorrow morning 10am" → `schedule` with `title="Buy milk at 6pm`
- "Don't want to buy milk anymore" → `delete` with `title="Buy milk at 10am"`
- Ambiguous commands → `none` with a friendly `message` explaining what’s missing

## Features
- Live microphone capture.
- WebSocket streaming.
- Azure Speech transcription with end-of-silence detection
- Intent parsing via Gemini into a strict JSON action schema
- In-memory todo store with actions: create, fetch, delete, schedule
- Primary Todo List UI (card-based) and secondary Recent Actions feed
- Special handling for `none` actions to provide feedback without clutter

## Project Layout
- `main.py` — FastAPI WebSocket endpoint at `/asr/premium`; wiring Azure Speech + LLM + todo store
- `llm.py` — Gemini integration and prompt construction
- `setting.py` — `.env` loading and typed settings via `pydantic-settings`
- `util.py` — response post-processing (e.g., add RFC3339 `scheduled_time` on create; degrade to `none` with friendly messages when task matching fails)
- `todo.py` — in-memory todo store and action handlers
- `vercel/index.html` — UI prototypes that stream audio to the server and render todos and recent actions

## Dependencies

Server (Python):
- `python >= 3.10`
- `fastapi`
- `uvicorn`
- `azure-cognitiveservices-speech`
- `google-generativeai`
- `pydantic-settings`
- `python-dotenv`

Frontend:
- Modern browser with microphone permissions (localhost allowed)

Cloud/API:
- Azure Speech resource (key and region)
- Google Gemini API key

## Configuration
Create a `.env` file in the project root:

```
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SERVICE_REGION=your-azure-region
GEMINI_API_KEY=your-gemini-key
```

`setting.py` loads `.env` automatically; environment variables are available to `main.py` and `llm.py`.

## Install

```
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install fastapi uvicorn azure-cognitiveservices-speech google-generativeai pydantic-settings python-dotenv
```

## Run Locally

1) Start the server:

```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

2) Serve a UI (use any static server). Example:

```
python3 -m http.server 8001
```

Then open this UIs in your browser:
- `http://localhost:8001/vercel/index.html`

Browsers require mic permissions; running on `localhost` is allowed.

## How It Works

1) The UI captures audio via Web Audio API and streams buffers over WebSocket to `ws://localhost:8000/asr/premium`.
2) The server pushes audio into Azure `PushAudioInputStream`, performs continuous recognition, and on finalized results:
   - Sends an `ACKNOWLEDGED` message with the processed transcript.
   - Calls Gemini to convert the transcript into a JSON action.
   - Post-processes the action (e.g., sets RFC3339 `scheduled_time` for `create`, or converts failed matches into `none` with a friendly `message`).
   - Executes the action against the `TodoStore` and returns `PROCESSED` with the `ai_response`, `all_task`, and `selected_task`.
3) The UI updates the Todo List and Recent Actions. Recent actions are newest-first; only five are kept.

## Action Schema

The server and UI communicate using this schema:

```
{
  "action": "create" | "fetch" | "delete" | "schedule" | "none",
  "message": "short human-readable explanation",
  "task": {
    "index": number | null,
    "title": string,
    "description": string,
    "scheduled_time": "RFC3339" | "",
    "matched_indexes": number[]
  }
}
```

Event frames sent by the server:

```
// ACKNOWLEDGED
{
  "event_type": "ACKNOWLEDGED",
  "status": "success",
  "transcribed_text_processed": "..."
}

// PROCESSED
{
  "event_type": "PROCESSED",
  "status": "success",
  "transcribed_text_processed": "...",
  "ai_response": { ... },
  "all_task": { "status": "fetched", "tasks": [ ... ] },
  "selected_task": { ... }
}
```

## Notes
- The todo store is in-memory and resets on server restart.