# MonsoonMitra — Install & Deployment Guide

Covers running locally and deploying to a **free tier**. Read the box below first — nearly every deployment problem traces back to it.

---

## ⚠ The two variables that matter

MonsoonMitra deploys as **two separate applications**: a **backend** (FastAPI) and a **frontend** (static React SPA). They talk over HTTPS, so each must be told about the other. Miss either and the app loads but nothing works.

| Set on | Variable | Value | Why |
|---|---|---|---|
| **Frontend** | `VITE_API_BASE_URL` | Backend origin, e.g. `https://monsoon-api.vercel.app` | Tells the SPA where the API lives |
| **Backend** | `ALLOWED_ORIGINS` | Frontend origin, e.g. `https://monsoon-web.vercel.app` | CORS — the browser blocks the calls otherwise |

**Three rules that trip people up:**

1. **`VITE_API_BASE_URL` is baked in at build time.** Setting it without a **redeploy** does nothing. Any change ⇒ redeploy the frontend.
2. **Both values must be a bare origin**: scheme + host only. No quotes, no angle brackets, no trailing slash, no path.
   - ✅ `https://monsoon-api.vercel.app`
   - ❌ `"https://monsoon-api.vercel.app"` · `<https://monsoon-api.vercel.app>` · `https://monsoon-api.vercel.app/` · `https://monsoon-api.vercel.app/api/v1`
3. **They point at each other, not at themselves.** The frontend's `VITE_API_BASE_URL` must be the **backend** URL. Pointing it at the frontend makes the app call itself and silently fail.

> **Self-check built in:** if the frontend cannot reach the API, the app shows an amber banner at the top with the raw configured value, the URL it actually called, and the underlying error. Trust that banner — it tells you which of the above is wrong.

---

## Contents
- [Prerequisites](#prerequisites)
- [1. Run locally](#1-run-locally)
- [2. Deploy on Vercel (frontend + backend)](#2-deploy-on-vercel-frontend--backend)
- [3. Alternative: Render backend + static frontend](#3-alternative-render-backend--static-frontend)
- [4. Post-deploy verification](#4-post-deploy-verification)
- [5. Troubleshooting](#5-troubleshooting)
- [6. Free-tier notes](#6-free-tier-notes)

---

## Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | **3.10+** (3.11 recommended) | backend |
| Node.js | 18+ (20 recommended) | frontend |
| Docker | optional | one-command local run |
| Git | any | deploying from GitHub |
| Groq API key | free | live AI text (optional) |

**Free Groq key:** <https://console.groq.com> → **API Keys → Create API Key** → copy the `gsk_…` value. No card required.

> Without a key the app still runs end-to-end: weather, alerts, checklists, travel and location search all work, and AI text falls back to built-in English templates.

> **Python 3.9 will not work.** The backend uses modern type syntax. If you use conda, create a dedicated env (`conda create -n monsoon python=3.11`) rather than installing into `base`.

---

## 1. Run locally

### Option A — Docker (one command)

```bash
cp .env.example .env      # then set GROQ_API_KEY=gsk_...  (optional)
docker compose up --build
```

Frontend → <http://localhost:5173> · API docs → <http://localhost:8000/docs>

### Option B — No Docker

**Backend (terminal 1):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...                          # optional
uvicorn app.main:app --reload --port 8000
```

**Frontend (terminal 2):**
```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```

Locally, CORS already allows `http://localhost:5173` by default, so no extra config is needed.

---

## 2. Deploy on Vercel (frontend + backend)

You create **two Vercel projects from the same repository**, differing only by **Root Directory**. The repo already contains everything needed: `backend/api/index.py` (ASGI serverless entrypoint), `backend/vercel.json`, and `frontend/vercel.json`.

### Step 0 — Push to GitHub

```bash
git init && git add . && git commit -m "MonsoonMitra"
git remote add origin https://github.com/<you>/monsoon-mitra.git
git push -u origin main
```

`.env` is git-ignored — secrets go in the Vercel dashboard, never in the repo.

### Step 1 — Backend project

1. Vercel → **Add New → Project** → import the repo.
2. **Root Directory: `backend`.** Vercel auto-detects Python from `requirements.txt` + the `api/` folder. Leave build/output settings empty.
3. **Environment Variables:**

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | `gsk_…` (mark as secret) |
   | `LLM_MODEL` | `llama-3.3-70b-versatile` |
   | `APP_ENV` | `production` |

   Leave `ALLOWED_ORIGINS` for Step 3 — you need the frontend URL first.
4. **Deploy.** Note the resulting URL, e.g. `https://monsoon-api.vercel.app`.
5. **Verify before continuing** — open in a browser:
   ```
   https://<backend>.vercel.app/api/v1/health
   ```
   Expect `{"status":"ok","llm_enabled":true,...}`. If this doesn't work, no amount of frontend config will help — fix it here first.

### Step 2 — Frontend project

1. **Add New → Project** → import the **same repo** again.
2. **Root Directory: `frontend`** (framework preset **Vite**, auto-detected).
3. **Environment Variable:**
   ```
   VITE_API_BASE_URL = https://<backend>.vercel.app
   ```
   Bare origin — see the rules at the top.
4. **Deploy.** Note the URL, e.g. `https://monsoon-web.vercel.app`.

### Step 3 — Connect them (CORS) and redeploy both

1. **Backend** project → Settings → Environment Variables:
   ```
   ALLOWED_ORIGINS = https://<frontend>.vercel.app
   ```
2. **Redeploy the backend** (picks up `ALLOWED_ORIGINS`).
3. **Redeploy the frontend** (bakes in `VITE_API_BASE_URL`).

Both redeploys are required. Open the site — the amber banner should be gone.

---

## 3. Alternative: Render backend + static frontend

Render supports long-running processes, so the SSE alert stream works there (Vercel is serverless, so the web client uses polling — see [free-tier notes](#6-free-tier-notes)).

**Backend on Render (free web service, no credit card, 750 hrs/month):**

Easiest is the included blueprint — Render → **New → Blueprint** → select the repo (it reads `render.yaml` and creates both services). Or manually:

- **Root Directory:** `backend`
- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/v1/health`
- **Env:** `GROQ_API_KEY`, `APP_ENV=production`, `ALLOWED_ORIGINS=<frontend origin>`

**Frontend** — deploy `frontend/` to Vercel, Netlify (`netlify.toml` included), Cloudflare Pages, or a Render Static Site. Build `npm run build`, output `dist`, and set `VITE_API_BASE_URL` to the Render backend URL.

The same two-variable rule applies exactly as above.

---

## 4. Post-deploy verification

Work through these in order — each isolates one layer:

1. **Backend alive:** `https://<backend>/api/v1/health` returns `{"status":"ok"}`.
2. **AI enabled:** the same response shows `"llm_enabled": true`. If `false`, `GROQ_API_KEY` isn't set on the backend (the app still works using templates).
3. **Frontend loads** with **no amber banner**. If the banner appears, read it — it names the raw value and the URL actually called.
4. **Location resolves:** allow location access (or search a city) — the chip under the header shows a real place name and coordinates.
5. **Plan generates:** click **Generate my plan** and confirm a plan appears.
6. **Multilingual:** switch the language selector and regenerate — AI content returns in that language.
7. **No CORS errors** in the browser console (F12).

---

## 5. Troubleshooting

**Amber "Cannot reach the MonsoonMitra API" banner**
The definitive diagnostic. It prints the raw `VITE_API_BASE_URL`, the URL actually called, and the error.
- Banner shows `(same origin)` ⇒ the configured value **isn't a valid URL**, so the app fell back to calling itself. Fix the value (quotes/brackets/whitespace are the usual cause) and redeploy the frontend.
- Banner shows your **frontend** URL ⇒ you pointed `VITE_API_BASE_URL` at the wrong app.
- Banner shows the correct backend URL ⇒ the backend is down or CORS is wrong. Test the health URL directly.

**Errors like "URL is not valid or contains user credentials" or "The string did not match the expected pattern"**
Safari/WebKit's way of saying the request URL is malformed — i.e. a bad `VITE_API_BASE_URL`. Safari is stricter than Chrome, so a value that "looks fine" elsewhere can fail here. Use a bare origin and redeploy.

**Location name shows "My location" instead of a place**
Reverse geocoding couldn't resolve the coordinates. The app falls back to a direct browser lookup, so if you see this alongside the banner, fix connectivity first.

**Plans return English despite choosing another language**
`llm_enabled` is `false` — the offline template fallback is English-only. Set `GROQ_API_KEY` on the backend and redeploy.

**`SystemError: pydantic-core version incompatible` / `ModuleNotFoundError` locally**
A mixed Python environment. Create a clean env on **Python 3.11** and reinstall:
```bash
conda create -n monsoon python=3.11 -y && conda activate monsoon
cd backend && pip install -r requirements.txt
```

**First request after idle is slow**
Free-tier cold start (Vercel functions and Render free services sleep when idle). Subsequent requests are fast.

**429 responses** — per-IP rate limit hit. Raise `RATE_LIMIT` (default `30/minute`).

---

## 6. Free-tier notes

| Concern | Reality | Mitigation |
|---|---|---|
| Cold starts | Vercel functions and Render free services sleep when idle | Acceptable for pilots; a cron ping or paid tier removes it |
| Alert updates | Web client **polls** `/api/v1/alerts` every 60s — works on serverless | Backend also exposes SSE (`/alerts/stream`) for streaming-capable hosts like Render |
| Function timeout (Vercel) | `maxDuration` set to 30s in `backend/vercel.json` | Groq calls normally finish in a few seconds |
| Groq quota | Generous free limits, but finite | On any LLM error the app auto-falls back to templates — it never breaks |
| Weather / geocoding | Open-Meteo + BigDataCloud: free, keyless | Responses cached server-side (`CACHE_TTL_SECONDS`, default 15 min) |
| Shared cache | In-memory, per-instance | Set `REDIS_URL` (e.g. Upstash free tier) if running multiple instances |
| Secrets | Never commit `.env` | Set `GROQ_API_KEY` only in the host dashboard |

### Full environment variable reference

**Backend**

| Var | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | Groq key. Empty ⇒ template mode. |
| `LLM_PROVIDER` | `groq` | `groq` \| `template` |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model id |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | **CORS allowlist — set to your frontend origin** |
| `APP_ENV` | `development` | `production` enables HSTS |
| `RATE_LIMIT` | `30/minute` | Per-IP limit |
| `CACHE_TTL_SECONDS` | `900` | Weather/AI cache TTL |
| `REDIS_URL` | — | Optional shared cache |
| `LOG_LEVEL` | `INFO` | Log verbosity |

**Frontend**

| Var | Purpose |
|---|---|
| `VITE_API_BASE_URL` | **Backend origin. Baked in at build time — redeploy after changing.** |

---

_MonsoonMitra is a reference implementation and not a substitute for official IMD/NDMA warnings. In an emergency, call **112**._
