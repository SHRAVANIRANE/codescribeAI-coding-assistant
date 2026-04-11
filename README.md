# 🤖 CodeScribeAI

CodeScribeAI is a local-first coding assistant with:

- FastAPI backend
- React + Vite frontend
- GitHub repository analysis
- Ollama-powered AI responses

## UI
<img width="1874" height="878" alt="image" src="https://github.com/user-attachments/assets/ce26b35b-2b46-45b7-9b2d-8c555f59c0cf" />
<img width="1886" height="893" alt="image" src="https://github.com/user-attachments/assets/73121360-9bf9-45f6-bd26-233ec7166536" />
<img width="1903" height="813" alt="image" src="https://github.com/user-attachments/assets/471f902f-07d5-4d90-8b62-64c30e2f8ad4" />




## Current Architecture

- Backend: `main.py` (FastAPI)
- Frontend: `frontend/` (React, Vite)
- Session store: SQLite (`sessions.db`)
- Optional async workers: Celery + Redis

## Prerequisites

- Python 3.10+
- Node.js 18+
- Ollama installed and running
- (Optional) Redis for async chat endpoints

## Environment Setup

1. Copy `.env.example` to `.env`
2. Fill real credentials and secrets

```bash
cp .env.example .env
```

Required keys:

```env
APP_ENV=development
SECRET_KEY=replace-with-a-long-random-string
FRONTEND_URL=http://localhost:5173
SESSION_TTL_SECONDS=3600
SESSION_STORE_TYPE=sqlite  # or "redis"
SESSIONS_DB_PATH=sessions.db
REDIS_URL=redis://localhost:6379/0
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_TOKEN=your_github_token
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=phi3:mini
OLLAMA_FALLBACK_MODELS=
```

Optional async keys:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Install

### Backend

```bash
# from repo root
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Pre-commit (format + lint hooks)

```bash
# after installing requirements
pre-commit install
pre-commit run --all-files
```

(If you're using a different shell, use the same commands with the appropriate activation step.)

### Frontend

```bash
cd frontend
npm install
```

## Run Locally

### 1) Start Ollama

```bash
ollama serve
ollama pull phi3:mini
```

### 2) Start backend

```bash
# from repo root
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3) Start frontend

```bash
cd frontend
npm run dev
```

Open: `http://localhost:5173`

## Optional: Async Worker (Celery)

Only needed if you use async task endpoints.

```bash
# requires Redis running
.\venv\Scripts\Activate.ps1
celery -A main:celery_app worker --loglevel=info --pool=solo
```

## Testing and Quality

### Backend tests

```bash
python -m unittest discover -s tests -v
```

### Frontend lint

```bash
cd frontend
npm run lint
```

## Key API Endpoints

- `GET /health`
- `GET /api/ai-status`
- `POST /api/chat`
- `POST /api/chat-async` (optional, Celery)
- `GET /repos/{username}`
- `GET /repos/{owner}/{repo}/files?recursive=true`
- `GET /repos/{owner}/{repo}/file-content?path=...`

## Security Notes

- Never commit `.env`.
- Rotate any leaked credentials immediately.
- For non-development environments:
  - set a strong `SECRET_KEY`
  - use secure deployment secrets management

## Production Readiness

See `PRODUCTION_READINESS.md` for checklist and current status.
