"""
KissanFlow FastAPI Application Entry Point.
Mounts all routers, CORS middleware, Socket.IO, and starts APScheduler.

Run with: uvicorn app.main:app --reload
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.socketio_server import sio
from app.scheduler import setup_scheduler

# Import all routers
from app.routers.auth import router as auth_router
from app.routers.farmers import router as farmers_router
from app.routers.crops import router as crops_router
from app.routers.centres import router as centres_router
from app.routers.bookings import router as bookings_router
from app.routers.queue import router as queue_router
from app.routers.transactions import router as transactions_router
from app.routers.grievances import router as grievances_router
from app.routers.notifications import router as notifications_router
from app.routers.dashboard import mandi_router, govt_router
from app.routers.analytics import analytics_router, mock_router
from app.routers.admin import router as admin_router
from app.routers.ivr import router as ivr_router

CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Ensure schema exists, start APScheduler on startup, shutdown on exit."""
    from seed import create_tables, add_missing_columns
    try:
        await create_tables()
        await add_missing_columns()
    except Exception as exc:
        # A read-only or not-yet-reachable database should not block startup;
        # the init container (docker) handles schema setup instead.
        print(f"[KissanFlow] Schema check skipped: {exc}")
    scheduler = setup_scheduler()
    scheduler.start()
    print("[KissanFlow] APScheduler started with 3 background jobs.")
    yield
    scheduler.shutdown(wait=False)
    print("[KissanFlow] APScheduler shut down.")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

fastapi_app = FastAPI(
    title="KissanFlow API",
    version="1.0.0",
    description="Agricultural procurement management platform — SIH 2024",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — allow frontend origins (Vite dev server + production)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        CLIENT_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount Routers ────────────────────────────────────────────────────────────

fastapi_app.include_router(auth_router,          prefix="/api/auth")
fastapi_app.include_router(farmers_router,       prefix="/api/farmers")
fastapi_app.include_router(crops_router,         prefix="/api/crops")
fastapi_app.include_router(centres_router,       prefix="/api/centres")
fastapi_app.include_router(bookings_router,      prefix="/api/bookings")
fastapi_app.include_router(queue_router,         prefix="/api/queue")
fastapi_app.include_router(transactions_router,  prefix="/api/transactions")
fastapi_app.include_router(grievances_router,    prefix="/api/grievances")
fastapi_app.include_router(notifications_router, prefix="/api/notifications")
fastapi_app.include_router(mandi_router,         prefix="/api/dashboard/mandi")
fastapi_app.include_router(govt_router,          prefix="/api/dashboard/govt")
fastapi_app.include_router(analytics_router,     prefix="/api/analytics")
fastapi_app.include_router(mock_router,          prefix="/api/mock")
fastapi_app.include_router(admin_router,         prefix="/api/admin")
fastapi_app.include_router(ivr_router,           prefix="/api/ivr")  # Twilio webhooks — no JWT auth


@fastapi_app.get("/health")
async def health_check():
    return {"status": "ok", "service": "KissanFlow API", "version": "1.0.0"}


# ─── Socket.IO ASGI wrapper exposed as 'app' for uvicorn ─────────────────────
# uvicorn app.main:app --reload  handles both REST API + WebSocket (Socket.IO)

# Keep Socket.IO below /ws so it works through both the Vite and Nginx proxies.
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="ws/socket.io")
