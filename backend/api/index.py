"""Vercel serverless entrypoint.

Vercel's Python runtime serves the ASGI `app` exported here. All routes are
rewritten to this function via backend/vercel.json, and FastAPI does the
internal routing. (Local/Docker/Render still use `uvicorn app.main:app`.)
"""
from app.main import app  # noqa: F401  (re-exported for the Vercel runtime)
