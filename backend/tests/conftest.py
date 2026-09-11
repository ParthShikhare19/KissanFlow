"""Pytest configuration: async SQLite test database + HTTP client fixtures."""
import asyncio
import os
import pathlib
import uuid

# Configure environment BEFORE any app import (app.database reads DATABASE_URL
# at import time). File-based SQLite so all connections share one database.
_TEST_DB_PATH = pathlib.Path(__file__).parent / "_test_kissanflow.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["ENVIRONMENT"] = "testing"
os.environ["JWT_SECRET"] = "test-jwt-secret-0123456789abcdef"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret-0123456789abcdef"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine, AsyncSessionLocal
from app.models.procurement_centre import ProcurementCentre
from app.models.crop import Crop, CropSeason
from app.models.user import User, UserRole
from app.models.farmer_profile import FarmerProfile
from app.models.slot_booking import SlotBooking, BookingStatus
from app.models.queue_entry import QueueEntry, QueueStatus
from app.models.transaction import Transaction, QualityStatus, ProcurementStatus, PaymentStatus
from app.utils.security import hash_password
from app.utils.qr_generator import generate_qr_base64

import json
from datetime import date, time, datetime, timezone, timedelta


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_database():
    """Create all tables once for the whole test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    try:
        os.remove(_TEST_DB_PATH)
    except OSError:
        pass


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_setup_database):
    """Wipe all rows between tests, then seed fresh baseline data."""
    async with engine.begin() as conn:
        from sqlalchemy import text
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'DELETE FROM "{table.name}"'))
    from tests.seed_test_data import seed_baseline
    async with AsyncSessionLocal() as db:
        await seed_baseline(db)
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    """Async HTTP client bound to the Socket.IO-wrapped FastAPI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def login(client: AsyncClient, mobile: str, password: str) -> str:
    """Login as a seeded user, return the access token."""
    res = await client.post("/api/auth/login", json={"mobile": mobile, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["data"]["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
