# CashTrace — Supabase Setup Guide

This guide walks you through provisioning, configuring, and verifying your Supabase database for CashTrace.

---

## 1. Create your Supabase Project (2 Minutes)

1. Navigate to [https://supabase.com](https://supabase.com) and sign in (or create a free account).
2. Click **"New Project"** and select your organization.
3. Fill in the project details:
   - **Name**: `CashTrace` (or `cashtrace`)
   - **Database Password**: Enter a strong password and save it somewhere secure.
   - **Region**: Choose the region closest to you (e.g., *South Asia (Mumbai)* or *East US*).
4. Click **"Create new project"** and wait ~1 minute for provisioning.

---

## 2. Deploy Schema & Tables

1. In your Supabase Dashboard, click on **SQL Editor** in the left sidebar (icon with `>_`).
2. Click **"New query"**.
3. Open [`supabase/schema.sql`](file:///c:/Users/Tanish/Desktop/CashTrace/supabase/schema.sql) in this repo, copy all its contents, and paste it into the SQL editor.
4. Click **"Run"** (or press `Ctrl + Enter`).
5. You will see `Success. No rows returned`.
6. Go to **Table Editor** to verify tables are created:
   - `profiles`
   - `accounts`
   - `transactions`
   - `balance_snapshots`
   - `dead_zone_events`
   - `scenarios`

---

## 3. (Optional) Load Realistic Seed Data

To populate sample trading accounts, transactions, and a detected Dead Zone event:

1. In the **SQL Editor**, click **"New query"**.
2. Open [`supabase/seed.sql`](file:///c:/Users/Tanish/Desktop/CashTrace/supabase/seed.sql), copy its contents, paste, and click **"Run"**.
3. Check the **Table Editor** — you will now see demo accounts, scheduled payroll & margin calls, and a sample detected liquidity dead zone.

---

## 4. Retrieve API Keys & Connection Strings

1. In the Supabase Dashboard, go to **Project Settings** (gear icon) -> **API** (or **Data API**).
2. Note down:
   - **Project URL** (e.g., `https://xyzabcdef.supabase.co`)
   - **anon / public key** (`eyJ...`)
   - **service_role key** (secret key for FastAPI administrative jobs)
3. Go to **Database** -> **Connection string** (URI) to get the direct PostgreSQL URI if needed:
   - `postgresql://postgres:[YOUR-PASSWORD]@db.xyzabcdef.supabase.co:5432/postgres`

---

## 5. Configure Environment Variables

### Backend (`backend/.env`)
Create `backend/.env` (from `backend/.env.example`):
```ini
FRONTEND_ORIGIN=http://localhost:3000

SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-ref.supabase.co:5432/postgres
```

### Frontend (`frontend/.env.local`)
Create `frontend/.env.local` (from `frontend/.env.local.example`):
```ini
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## 6. Verify Connection

1. **Frontend**: Run `npm install` inside `frontend/` then `npm run dev`. Open `http://localhost:3000` to see the live Supabase Status widget.
2. **Backend**: Run `uvicorn app.main:app --reload` inside `backend/`. Visit `http://localhost:8000/api/supabase/status` to test database reachability.
