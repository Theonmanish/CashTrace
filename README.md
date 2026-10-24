# CashTrace

Financial Dead Zone Detector — a Finance × Trading project for Hefty-Hacks 2026.

This repository currently contains **foundation scaffolding only**. The application, API contracts, and financial analysis logic have not been implemented yet.

## Directory structure

```text
frontend/           Next.js UI
backend/            FastAPI HTTP API
financial_engine/   Deterministic financial processing (reserved)
docs/               Shared architecture notes
```

The frontend, API, and financial engine are separate work areas. Teammates can install and run each part independently.

## Technology stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS
- Backend: Python, FastAPI
- Financial processing: Python module reserved for future Pandas/NumPy work

## Prerequisites

- Node.js 20+ and npm
- Python 3.11+ (3.13 is fine)

## Local setup

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Default URL: [http://localhost:3000](http://localhost:3000)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --app-dir .
```

Default URL: [http://localhost:8000](http://localhost:8000)

See `frontend/README.md` and `backend/README.md` for the same commands in slightly more detail. Architecture boundaries are described in `docs/architecture.md`.
