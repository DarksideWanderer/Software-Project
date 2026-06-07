# AI Service Layer

FastAPI-based AI service for the smart home assistant project.

Current MVP features:

- `GET /health`: health and capability check.
- `POST /ai/nlu`: rule-based Chinese command parsing.
- `POST /ai/asr`: mock ASR endpoint; real iFlytek integration can replace this later.

The AI service does not control devices directly. It returns structured JSON for the backend to dispatch.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

## Test

```bash
pytest
```
