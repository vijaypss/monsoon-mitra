# MonsoonMitra — Install & Deploy Guide

Two parts:
1. **[Run locally](#1-run-locally)** — three ways (Docker, manual, or backend-only).
2. **[Deploy on a free tier](#2-deploy-on-a-free-tier)** — backend on Render (free), frontend on Vercel/Netlify/Cloudflare/Render (free).

Everything the app depends on has a real free tier: **Groq** (LLM), **Open-Meteo** (weather, no key), and static + small-service hosting.

---

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.10+ | backend |
| Node.js | 18+ (20 recommended) | frontend |
| Docker + Docker Compose | any recent | the one-command path (optional) |
| Git | any | cloning / deploying |
| A **free Groq API key** | — | live AI text (optional — app runs without it) |

**Get a free Groq key:** sign in at <https://console.groq.com>, open **API Keys → Create API Key**, copy the `gsk_...` value. No card required.

> Without a key the app still runs end-to-end — AI text falls back to built-in templates (English). Weather, alerts, checklists and travel all work fully.

---

## 1. Run locally

### Option A — Docker (one command, recommended)

```bash
git clone <your-repo-url> monsoon-mitra
cd monsoon-mitra
cp .env.example .env
#   edit .env → set GROQ_API_KEY=gsk_...   (leave blank to use template mode)
docker compose up --build
```

Open:
- Web app → <http://localhost:5173>
- API docs (Swagger) → <http://localhost:8000/docs>
- Health → <http://localhost:8000/api/v1/health>

Stop with `Ctrl-C`, or `docker compose down`.

### Option B — Manual (no Docker)

**Backend (terminal 1):**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...          # optional; Windows: set GROQ_API_KEY=...
uvicorn app.main:app --reload --port 8000
```

**Frontend (terminal 2):**
```bash
cd frontend
npm install
# point the SPA at your local API:
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```

Open <http://localhost:5173>.

### Option C — Backend only (API / integration)

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --port 8000
# then:
curl -X POST localhost:8000/api/v1/plan -H 'Content-Type: application/json' -d '{
  "location": {"lat":19.076,"lon":72.877,"name":"Mumbai"},
  "household": {"adults":2,"children":1,"seniors":1,"dwelling":"apartment",
                "floor":0,"medical_needs":["diabetes"],"has_vehicle":true,"pets":1},
  "language": "hi"
}'
```

### Handy shortcuts (Makefile)

```bash
make install   # install backend + frontend deps
make test      # run backend tests
make lint      # ruff
make up        # docker compose up --build
```

---

## 2. Deploy on a free tier

Architecture in production = **two deployables**:

```
[ Static frontend ]  ──HTTPS──►  [ FastAPI backend ]  ──►  Groq + Open-Meteo
  Vercel/Netlify/                  Render free web
  Cloudflare/Render                service
```

You deploy the **backend first** (to get its URL), then the **frontend** (pointed at that URL), then set **CORS** on the backend back to the frontend URL. Do them in that order.

### Step 1 — Push your code to GitHub

```bash
git init && git add . && git commit -m "MonsoonMitra"
git branch -M main
git remote add origin https://github.com/<you>/monsoon-mitra.git
git push -u origin main
```

`.env` is git-ignored — your key never leaves your machine. You'll set it as a secret in the dashboard instead.

### Step 2 — Deploy the backend on Render (free)

Render's free web service needs **no credit card** and gives **750 instance-hours/month**. Note: free services **sleep after ~15 min idle** and take ~1 min to wake on the next request (fine for a demo/pilot).

**Fastest path — Blueprint (uses the included `render.yaml`):**
1. Go to <https://dashboard.render.com> → **New → Blueprint**.
2. Connect your GitHub repo. Render reads `render.yaml` and proposes **both** the API and the static site.
3. When prompted, set the secret **`GROQ_API_KEY`** = your `gsk_...` (leave other vars as-is for now).
4. Click **Apply**. Wait for the API to go live at `https://monsoon-mitra-api.onrender.com`.

**Manual path (no blueprint):**
1. **New → Web Service** → pick the repo.
2. Settings:
   - **Root Directory:** `backend`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/api/v1/health`
   - **Instance Type:** Free
3. **Environment** → add:
   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `GROQ_API_KEY` | `gsk_...` (mark as secret) |
   | `LLM_MODEL` | `llama-3.3-70b-versatile` |
   | `RATE_LIMIT` | `30/minute` |
   | `ALLOWED_ORIGINS` | *(fill in after Step 3)* |
4. **Create Web Service.** Verify: open `https://<your-api>.onrender.com/api/v1/health` → `{"status":"ok",...}`.

> **Alternative — Hugging Face Spaces (free CPU, Docker):** create a **Docker Space**, push the `backend/` folder, and change the Dockerfile's exposed port to **7860** (`--port 7860`; HF only serves 7860). Free CPU Space is 2 vCPU / 16 GB, sleeps after 48 h idle. Fly.io and Google Cloud Run free tiers also work with the included `backend/Dockerfile`.

### Step 3 — Deploy the frontend (free static hosting)

Pick **one**. Set the env var `VITE_API_BASE_URL` to your backend URL from Step 2 (it's read at build time).

**Vercel** (`frontend/vercel.json` included):
1. <https://vercel.com> → **Add New → Project** → import the repo.
2. **Root Directory:** `frontend`. Framework preset: **Vite** (auto).
3. **Environment Variables:** `VITE_API_BASE_URL = https://<your-api>.onrender.com`
4. **Deploy** → you get `https://<project>.vercel.app`.

**Netlify** (`frontend/netlify.toml` included):
1. <https://app.netlify.com> → **Add new site → Import from Git**.
2. **Base directory:** `frontend` · **Build:** `npm run build` · **Publish:** `frontend/dist`.
3. **Site settings → Environment variables:** `VITE_API_BASE_URL = https://<your-api>.onrender.com` → **Redeploy**.

**Cloudflare Pages:** Framework preset **Vite**, build `npm run build`, output `dist`, root `frontend`, add the same env var.

**Or Render Static Site:** already defined in `render.yaml` (`monsoon-mitra-web`) — deployed with the blueprint in Step 2. Just set its `VITE_API_BASE_URL`.

---

## 2b. Alternative: everything on Vercel (frontend **and** backend)

Vercel runs Python as **serverless functions**, so the backend deploys via the included
`backend/api/index.py` (ASGI entrypoint) + `backend/vercel.json` (routes all paths to it).
You create **two Vercel projects from the same repo** — one rooted at `backend`, one at `frontend`.

### A. Backend project (FastAPI serverless)
1. <https://vercel.com> → **Add New → Project** → import the repo.
2. **Root Directory:** `backend`. Vercel auto-detects Python from `requirements.txt` + the `api/` folder — leave build/output settings empty.
3. **Environment Variables:**
   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | `gsk_...` |
   | `LLM_MODEL` | `llama-3.3-70b-versatile` |
   | `APP_ENV` | `production` |
   | `ALLOWED_ORIGINS` | *(fill in after the frontend is live)* |
4. **Deploy.** Verify: `https://<backend>.vercel.app/api/v1/health` → `{"status":"ok"}`.

### B. Frontend project (static SPA)
1. **Add New → Project** → same repo again.
2. **Root Directory:** `frontend` (framework preset **Vite**, auto).
3. **Environment Variable:** `VITE_API_BASE_URL = https://<backend>.vercel.app`
4. **Deploy** → `https://<frontend>.vercel.app`.

### C. CORS
In the **backend** project → Settings → Environment Variables, set
`ALLOWED_ORIGINS = https://<frontend>.vercel.app` → **Redeploy**.

### Vercel caveats (important)
- **Alerts use polling, so they work on Vercel.** The web client refreshes `/api/v1/alerts` every 60s (no long-lived connection needed). The backend still exposes an SSE endpoint (`/api/v1/alerts/stream`) for hosts that support streaming, like Render — it's simply unused by the web client.
- **Function timeout:** free tier caps duration (`maxDuration` set to 30s in `vercel.json`); Groq calls normally finish in a few seconds.
- **Cold starts** on first request after idle, similar to Render.
- **No shared cache** across serverless invocations (in-memory cache is per-instance); fine functionally, or add `REDIS_URL` (e.g. Upstash free) for a shared cache.

---

### Step 4 — Wire up CORS (important)

The browser will block calls until the backend allows the frontend's origin.

1. In Render → your **API service → Environment**, set:
   ```
   ALLOWED_ORIGINS = https://<your-frontend-domain>
   ```
   (comma-separate if you have several, e.g. a Vercel preview + prod domain). No trailing slash.
2. Save → the service redeploys automatically.
3. Reload the frontend and generate a plan. Done. ✅

---

## Post-deploy checklist

- [ ] `GET https://<api>/api/v1/health` returns `"status":"ok"` and shows `"llm_enabled": true` (confirms the Groq key is picked up).
- [ ] Frontend loads and **Generate my plan** returns a plan (check the browser Network tab — the request should hit your API domain, not localhost).
- [ ] No CORS errors in the browser console (if there are, re-check `ALLOWED_ORIGINS`).
- [ ] Switch the language selector — AI output comes back translated.
- [ ] Docs are reachable at `https://<api>/docs`.

## Free-tier limits & tips

| Concern | Reality on free tier | Mitigation |
|---|---|---|
| Backend cold start | Render free sleeps after ~15 min idle (~1 min wake) | Acceptable for pilots; a cron ping or paid instance removes it |
| Groq rate/quota | Generous free limits, but finite | App auto-falls back to templates on any LLM error — never breaks |
| Weather calls | Open-Meteo free & keyless | Responses cached server-side (`CACHE_TTL_SECONDS`, default 15 min) |
| Secrets | Never commit `.env` | Set `GROQ_API_KEY` only in the host's dashboard |
| Shared cache across replicas | In-memory by default | Set `REDIS_URL` (e.g. Upstash free tier) if you scale to >1 instance |

## Troubleshooting

- **CORS error in console** → `ALLOWED_ORIGINS` on the backend must exactly match the frontend origin (scheme + host, no trailing slash).
- **Frontend calls `localhost:8000` in production** → `VITE_API_BASE_URL` wasn't set at build time; set it and redeploy (it's baked into the build).
- **`llm_enabled: false` in `/health`** → `GROQ_API_KEY` isn't set on the backend host, or `LLM_PROVIDER=template`.
- **First request after idle is slow** → free-tier cold start; subsequent requests are fast.
- **429 responses** → you hit the per-IP rate limit; raise `RATE_LIMIT`.

---

_Reminder: MonsoonMitra is a reference implementation and not a substitute for official IMD/NDMA warnings. In an emergency, call 112._
