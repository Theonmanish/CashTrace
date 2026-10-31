# CashTrace — Production Deployment Guide
## Backend on Render + Frontend on Vercel

This guide covers deploying the FastAPI backend to [Render](https://render.com) and the Next.js frontend to [Vercel](https://vercel.com).

---

## 1. Push your Code to GitHub

Make sure all recent configuration files are committed and pushed to your GitHub repository:

```bash
git add .
git commit -m "Configure Supabase and production deployment settings"
git push origin main
```

---

## 2. Deploy Backend on Render

Deploy the backend first so you have the live backend URL to plug into Vercel.

### Method A: Using the Render Blueprint (Recommended - 1 Click)

1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** ➔ **Blueprint**.
3. Select your `CashTrace` GitHub repository.
4. Render will automatically read [`render.yaml`](file:///c:/Users/Tanish/Desktop/CashTrace/render.yaml) and configure the service.
5. In the prompt, enter your environment variables (from your `backend/.env`):
   - `SUPABASE_URL`: `https://pnfvnoahymfujkitjlfj.supabase.co`
   - `SUPABASE_KEY`: Your anon/public key
   - `SUPABASE_SERVICE_ROLE_KEY`: Your service role key
   - `DATABASE_URL`: `postgresql://postgres:If2C08Ib1234@db.pnfvnoahymfujkitjlfj.supabase.co:5432/postgres`
   - `FRONTEND_ORIGIN`: `http://localhost:3000` (you will add your Vercel URL here in Step 4)
6. Click **Apply**.
7. Once deployed, copy your Render service URL (e.g., `https://cashtrace-backend.onrender.com`).

---

### Method B: Manual Web Service on Render

If you prefer setting it up manually:

1. Click **New +** ➔ **Web Service**.
2. Connect your GitHub repository.
3. Set the following fields:
   - **Name**: `cashtrace-backend`
   - **Region**: Choose closest to you (e.g., Singapore or Frankfurt/Oregon)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
4. Under **Advanced** ➔ **Health Check Path**, enter `/health`.
5. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `SUPABASE_URL`: `https://pnfvnoahymfujkitjlfj.supabase.co`
   - `SUPABASE_KEY`: *(your Supabase anon key)*
   - `SUPABASE_SERVICE_ROLE_KEY`: *(your Supabase service role key)*
   - `DATABASE_URL`: `postgresql://postgres:If2C08Ib1234@db.pnfvnoahymfujkitjlfj.supabase.co:5432/postgres`
   - `FRONTEND_ORIGIN`: `http://localhost:3000`
6. Click **Create Web Service**.
7. Copy your backend URL once live: `https://cashtrace-backend.onrender.com`.

---

## 3. Deploy Frontend on Vercel

1. Log in to [vercel.com](https://vercel.com) and click **Add New...** ➔ **Project**.
2. Import your `CashTrace` GitHub repository.
3. In the project configuration screen:
   - **Project Name**: `cashtrace`
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click **Edit** and select **`frontend`** (Critical!)
4. Expand **Environment Variables** and add the following:
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://pnfvnoahymfujkitjlfj.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: *(your Supabase anon key)*
   - `NEXT_PUBLIC_BACKEND_URL`: `https://cashtrace-backend.onrender.com` *(your Render URL from Step 2)*
5. Click **Deploy**.
6. Vercel will build and deploy the frontend, assigning a production URL (e.g., `https://cashtrace.vercel.app`).

---

## 4. Final Connection: Update CORS on Render

Now that you have your live Vercel domain:

1. Go to your **Render Dashboard** ➔ Click your `cashtrace-backend` service.
2. Go to **Environment** tab.
3. Update `FRONTEND_ORIGIN` to include your Vercel domain:
   ```env
   FRONTEND_ORIGIN=http://localhost:3000,https://cashtrace.vercel.app
   ```
4. Click **Save Changes**. Render will automatically redeploy with the updated CORS policy.
*(Note: The backend is also preconfigured with regex matching `https://.*\.vercel\.app`, so any future PR/preview deployments on Vercel work automatically!)*

---

## 5. Verification Checklist

- [ ] Render health check: Open `https://cashtrace-backend.onrender.com/health` ➔ returns `{"status": "ok"}`
- [ ] Render Supabase status: Open `https://cashtrace-backend.onrender.com/api/supabase/status` ➔ returns `{"configured": true, "connected": true, ...}`
- [ ] Vercel UI: Open `https://cashtrace.vercel.app` ➔ Status badge shows green `Connected`
