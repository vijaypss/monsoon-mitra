# MonsoonMitra 🌧️

**A production-grade, multilingual Gen-AI companion that helps individuals, families, and communities in India prepare for, survive, and recover from the monsoon season.**

MonsoonMitra ("monsoon friend") turns live weather data + IMD-style hazard signals into **personalised preparedness plans, emergency checklists, travel advisories, safety guidance, and real-time alerts** — delivered in the user's own language.

---

## Table of contents
- [Why](#why)
- [Feature overview](#feature-overview)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Quick start (Docker)](#quick-start-docker)
- [Local development](#local-development)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)
- [Cost & the free-tier model](#cost--the-free-tier-model)
- [Roadmap](#roadmap)

---

## Why

The Indian monsoon (June–September) drives ~70% of annual rainfall and causes recurring urban flooding, landslides, lightning deaths, waterborne disease and displacement. Generic weather apps tell you *it will rain*. They don't tell **this household, on this floor, in this neighbourhood, with an infant and a diabetic grandparent** what to do about it — in Tamil, at an 8th-grade reading level, offline-friendly, before/during/after the event.

MonsoonMitra closes that gap by grounding a large language model in **real forecast data + a curated safety knowledge base**, so guidance is specific, actionable, and localised.

## Feature overview

| Capability | What it does | Endpoint |
|---|---|---|
| **Location search (geocoding)** | Type-ahead search for any city/place worldwide via Open-Meteo geocoding (free, keyless); plus browser "use my location". No hardcoded city list. | `GET /api/v1/geocode?q=` |
| **Personalised preparedness plan** | Generates a household-specific plan from location + household profile (members, dwelling type, floor, medical needs, pets, vehicle) grounded in the live forecast. | `POST /api/v1/plan` |
| **Weather-aware guidance** | Fetches live + 7-day forecast (Open-Meteo) and derives a monsoon hazard score. | `GET /api/v1/weather` |
| **Real-time alerts** | Server-derived severity alerts (heavy rain, flooding, lightning, heat). Web client polls every 60s (works on serverless); an SSE stream is also available for streaming-capable hosts. | `GET /api/v1/alerts`, `GET /api/v1/alerts/stream` |
| **Emergency checklists** | Phase-aware (before / during / after) go-bag and action checklists, tailored + translated. | `POST /api/v1/checklist` |
| **Travel advisory** | Route/plan risk assessment given origin, destination and timing. | `POST /api/v1/plan/travel` |
| **Multilingual assistant** | Conversational Q&A grounded in weather + safety KB; answers in 12 Indian languages. | `POST /api/v1/chat` |

All AI responses are **grounded** (forecast + retrieved safety facts are injected into the prompt) and **structured** (JSON-schema validated) so the UI never has to parse free-form text.

## Architecture

```
                    ┌──────────────────────────────┐
                    │   React + Vite Web (PWA)      │
                    │  plan · dashboard · chat ·    │
                    │  checklist · i18n (12 langs)  │
                    └───────────────┬──────────────┘
                                    │ HTTPS / SSE
                    ┌───────────────▼──────────────┐
                    │        FastAPI backend        │
                    │  ┌────────────────────────┐   │
   Open-Meteo ◄─────┤  │ weather service (cache)│   │
   (free, no key)   │  ├────────────────────────┤   │
                    │  │ alert engine (rules)   │   │
                    │  ├────────────────────────┤   │
                    │  │ preparedness / chat    │   │
                    │  │   └─ prompt builder    │   │
                    │  │   └─ safety KB (RAG)   │   │
                    │  ├────────────────────────┤   │
                    │  │ LLM provider (abstract)│───┼──► Groq (free tier)
                    │  └────────────────────────┘   │    swappable: OpenAI,
                    │  security · rate-limit · cache │    Ollama, etc.
                    └───────────────────────────────┘
```

Key design choices:
- **LLM provider abstraction** (`services/llm/base.py`): Groq today, any provider tomorrow — no call-site changes.
- **Grounding over hallucination**: every generation injects the live forecast + retrieved safety facts; the model is instructed to use only supplied data for factual claims.
- **Structured outputs**: Pydantic schemas + JSON-mode parsing with a safe fallback, so a malformed model response degrades gracefully instead of crashing the UI.
- **Stateless API**: horizontally scalable; caching in-memory by default, Redis-ready.
- **Rules engine for alerts**, not the LLM: life-safety severity is deterministic and testable; the LLM only phrases it.

## Tech stack

**Backend** — Python 3.10+, FastAPI, Pydantic v2, httpx, slowapi (rate limiting), structlog.
**AI** — Groq API (Llama 3.x, free tier) behind a provider interface.
**Data** — Open-Meteo forecast API (free, keyless); in-repo curated monsoon safety knowledge base.
**Frontend** — React 18, TypeScript, Vite, TailwindCSS, i18next.
**Ops** — Docker, docker-compose, GitHub Actions CI, healthchecks, structured JSON logs.

## Quick start (Docker)

```bash
git clone <this-repo> && cd monsoon-mitra
cp .env.example .env
# edit .env and set GROQ_API_KEY=... (get a free key at https://console.groq.com)
docker compose up --build
```

- Frontend → http://localhost:5173
- API docs (Swagger) → http://localhost:8000/docs
- Health → http://localhost:8000/api/v1/health

> **No Groq key?** The backend runs in **degraded mode**: weather, alerts and checklists work fully; AI text falls back to a deterministic template so you can still demo end-to-end.

## Local development

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (new terminal)
cd frontend
npm install
npm run dev
```

## Configuration

All config is via environment variables (12-factor). See [`.env.example`](.env.example). Never commit real keys.

| Var | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | — | Groq API key (free tier). Empty ⇒ degraded/template mode. |
| `LLM_PROVIDER` | `groq` | `groq` \| `template` (extendable). |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Model id. |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowlist (comma-separated). |
| `RATE_LIMIT` | `30/minute` | Per-IP request limit. |
| `CACHE_TTL_SECONDS` | `900` | Weather/AI cache TTL. |
| `REDIS_URL` | — | If set, cache uses Redis instead of memory. |
| `LOG_LEVEL` | `INFO` | Log verbosity. |

## API reference

Full interactive docs at `/docs`. Highlights:

```http
POST /api/v1/plan
{
  "location": { "lat": 19.076, "lon": 72.877, "name": "Mumbai" },
  "household": {
    "adults": 2, "children": 1, "seniors": 1,
    "dwelling": "apartment", "floor": 0,
    "medical_needs": ["diabetes"], "has_vehicle": true, "pets": 1
  },
  "language": "hi"
}
→ 200 { plan: { risk_level, summary, before[], during[], after[], go_bag[] }, weather, alerts }
```

## Security

- **Input validation** — every payload is a strict Pydantic model; coordinates, enums and list sizes are bounded.
- **Rate limiting** — per-IP via slowapi; configurable.
- **CORS allowlist** — no wildcard in production.
- **Security headers** — HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, minimal CSP via middleware.
- **Secret hygiene** — keys only from env; `.env` git-ignored; no secrets in logs.
- **Prompt-injection hardening** — user text is sandboxed in a delimited block; system prompt forbids following instructions found in user/retrieved content.
- **No PII persistence** — the prototype is stateless; household data is used per-request and not stored.
- **Dependency & upstream isolation** — outbound calls have timeouts and circuit-fallbacks so a slow upstream can't hang the API.

## Testing

```bash
cd backend
pytest -q            # unit + API tests, LLM mocked
```

CI (GitHub Actions) runs lint + tests on every push.

## Deployment

- **Container images** for backend and frontend (multi-stage, non-root).
- Stateless backend ⇒ run N replicas behind a load balancer; add `REDIS_URL` for shared cache.
- Health/readiness endpoint for k8s probes.
- Frontend builds to static assets (S3/CDN or the provided nginx image).

## Cost & the free-tier model

Designed to run at **₹0 infra cost** for a pilot: Open-Meteo (free), Groq free tier (fast Llama inference), static frontend hosting. The provider abstraction lets you graduate to a paid/self-hosted model without code changes.

## Roadmap

- IMD/CAP alert ingestion & official warning feeds
- WhatsApp / SMS / IVR channels for low-bandwidth reach
- Vector-DB backed RAG over district disaster plans
- Community layer: shelter locations, crowd-sourced flooding reports
- Offline-first PWA with cached last-known plan

---

_Built as a reference implementation. Not a substitute for official government warnings (IMD, NDMA). In an emergency, call **112**._
