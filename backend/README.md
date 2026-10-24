# CashTrace Backend

Minimal FastAPI service for local development. Business endpoints are not implemented yet.

## Setup

From the `backend/` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux, activate the virtual environment with `source .venv/bin/activate` and copy the env file with `cp .env.example .env`.

Edit `.env` if the frontend runs on an origin other than `http://localhost:3000`.

## Start the API

```powershell
uvicorn app.main:app --reload --app-dir .
```

The API is available at [http://localhost:8000](http://localhost:8000). Interactive docs are at [http://localhost:8000/docs](http://localhost:8000/docs).
