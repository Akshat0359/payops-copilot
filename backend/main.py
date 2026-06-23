"""
PayOps Copilot — FastAPI application entrypoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db

# Import all models so Base.metadata is populated before init_db() runs
import models.payment       # noqa: F401
import models.settlement    # noqa: F401
import models.refund        # noqa: F401
import models.chargeback    # noqa: F401
import models.bank_entry    # noqa: F401
import models.case          # noqa: F401

from routers import webhooks, ingest, cases, disputes, analytics

app = FastAPI(
    title="PayOps Copilot",
    description="AI-powered payments ops copilot",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(webhooks.router)
app.include_router(ingest.router)
app.include_router(cases.router)
app.include_router(disputes.router)
app.include_router(analytics.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {"status": "ok", "project": "PayOps Copilot"}
