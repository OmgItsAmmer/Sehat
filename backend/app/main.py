"""
Sehat API entrypoint.

WhatsApp intake (phase 1):
  WhatsApp → Green API → POST /api/whatsapp/webhook → print to console
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.whatsapp import router as whatsapp_router
from app.services import memory

console = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Sehat",
    description="AI-powered emergency intake triage",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(whatsapp_router, prefix="/api/whatsapp", tags=["whatsapp"])


@app.on_event("startup")
def on_startup() -> None:
    backend = "redis" if memory.is_redis_configured() else "in-memory"
    console.info("Sehat ready — WhatsApp webhooks: POST /api/whatsapp/webhook")
    console.info("Clinic API: GET /api/cases, /api/analytics, POST /api/chat/message")
    console.info("Session memory: %s", backend)
    console.info("Process PID %s (only one 'make dev' should own port 8000)", os.getpid())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await memory.close_redis()
