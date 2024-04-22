import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENV_STATE"] = "test"

from entertainment.config import config  # noqa
from entertainment.database import Base, get_db  # noqa
from entertainment.main import app  # noqa
from entertainment.models import Users, Movies  # noqa


# Creating test.db instead of using application db (entertainment.db)
engine = create_engine(
    config.DATABASE_URL,  # test.db
    connect_args={"check_same_thread": False},
    echo=False,
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


# Overriding database connection for all of the endpoins
def override_get_db():
    """Sets a clean db session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # for table in reversed(Base.metadata.sorted_tables):
        #     db.execute(table.delete())
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM movies"))
        # db.
        db.commit()
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Overriding fixture pytest.mark.anyio to test async functions
@pytest.fixture(scope="session")
def anyio_backend():
    """
    Overrides anyio.pytest_plugin fixture to return asyncio
    as a designated library for async fixtures.
    """
    return "asyncio"


# Creating test clients
@pytest.fixture
def client() -> Generator:
    """Yield TestClient() on tested app."""
    # app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)


@pytest.fixture
async def async_client(client) -> AsyncGenerator:
    """Uses async client from httpx instead of test client from fastapi for async tests."""
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac


# @pytest.fixture
def create_db_user(
    username,
    email,
    hashed_password,
    role="user",
    is_active=True,
    first_name=None,
    last_name=None,
):
    db = TestingSessionLocal()
    try:
        new_user = Users(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=is_active,
            first_name=first_name,
            last_name=last_name,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    finally:
        db.close()
