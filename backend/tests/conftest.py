"""
Shared pytest fixtures for in-memory SQLite test database.
All models must be imported here so Base.metadata is populated before create_all.
"""
import sys
import os

# Ensure backend/ is on path when running tests from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import database  # must import BEFORE models to ensure Base is the shared instance

# Import all models so their tables register onto Base.metadata
import models.payment       # noqa: F401
import models.settlement    # noqa: F401
import models.refund        # noqa: F401
import models.chargeback    # noqa: F401
import models.bank_entry    # noqa: F401
import models.case          # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)
    await engine.dispose()
