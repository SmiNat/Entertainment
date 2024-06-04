import datetime
import logging
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ["ENV_STATE"] = "test"

from entertainment.config import config  # noqa: E402
from entertainment.database import Base, get_db  # noqa: E402
from entertainment.main import app  # noqa: E402
from entertainment.models import Books, Games, Movies, Users  # noqa: E402
from entertainment.routers.auth import create_access_token  # noqa: E402

logger = logging.getLogger(__name__)


# Creating test.db database instead of using application db (entertainment.db)
engine = create_engine(
    config.DATABASE_URL,  # test.db
    connect_args={"check_same_thread": False},
    echo=False,
)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Overriding database connection for all of the endpoins
def override_get_db():
    """Sets a clean db session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Cleaning db tables after each test
@pytest.fixture(autouse=True, scope="function")
def clean_db():
    """Cleans db session for each test."""
    with TestingSessionLocal() as db:
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM movies"))
        db.execute(text("DELETE FROM books"))
        db.execute(text("DELETE FROM games"))
        db.execute(text("DROP TABLE IF EXISTS test_table;"))
        db.commit()


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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as ac:
        yield ac


# Some app fixtures to use in tests


@pytest.fixture
def created_admin_user() -> Users:
    db = TestingSessionLocal()
    try:
        admin_user = Users(
            username="adminuser",
            email="admin@example.com",
            hashed_password="#password",
            role="admin",
            is_active=True,
            first_name=None,
            last_name=None,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        return admin_user
    finally:
        db.close()


@pytest.fixture
async def registered_user(async_client: AsyncClient) -> dict:
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "confirm_password": "testpass123",
    }
    user = await async_client.post("/user/register", json=payload)
    return user.json()


@pytest.fixture
async def created_token(registered_user) -> str:
    token = create_access_token(
        username=registered_user["username"],
        user_id=registered_user["id"],
        role=registered_user["role"],
    )
    return token


@pytest.fixture
async def created_user_token(registered_user, created_token) -> tuple:
    user = registered_user
    token = created_token
    return user, token


@pytest.fixture()
async def added_movie() -> Movies:
    """Creates movie record in the database before running a test."""
    movie = Movies(
        title="Deadpool",
        premiere=datetime.date(2016, 2, 11),
        score=7.6,
        genres="Action, Adventure, Comedy",
        overview="The origin story of former Special Forces operative ....",
        crew="Ryan Reynolds, Wade Wilson / Deadpool, ...",
        orig_title="Deadpool",
        orig_lang="English",
        budget=58000000,
        revenue=781947691,
        country="AU",
        created_by="testuser",
    )

    db = TestingSessionLocal()
    try:
        db.add(movie)
        db.commit()
        db.refresh(movie)
        return movie
    finally:
        db.close()


@pytest.fixture()
async def added_book() -> Books:
    """Creates book record in the database before running a test."""
    book = Books(
        title="New book",
        author="John Doe",
        description=None,
        genres="Classics, Romance",
        avg_rating=3.2,
        num_ratings=1000,
        first_published=datetime.date(2011, 11, 11),
        created_by="testuser",
    )

    db = TestingSessionLocal()
    try:
        db.add(book)
        db.commit()
        db.refresh(book)
        return book
    finally:
        db.close()


@pytest.fixture
async def added_game() -> Games:
    """Creates games record in the database before running a test."""
    game = Games(
        title="New game",
        premiere=datetime.date(2011, 11, 11),
        developer="Avalanche Studios",
        publisher=None,
        genres="Action, RPG, Simulation, Indie",
        game_type="Co-op, Steam Cloud, Early Access",
        price_eur=None,
        price_discounted_eur=4.99,
        review_overall=None,
        review_detailed="Negative",
        reviews_positive=0.33,
        created_by="testuser",
    )
    db = TestingSessionLocal()
    try:
        db.add(game)
        db.commit()
        db.refresh(game)
        return game
    finally:
        db.close()
