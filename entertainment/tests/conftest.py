import logging
import os
from typing import AsyncGenerator, Generator
from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ["ENV_STATE"] = "test"

from entertainment.config import config  # noqa: E402
from entertainment.database import Base, get_db  # noqa: E402
from entertainment.enums import MovieGenres  # noqa: E402
from entertainment.main import app  # noqa: E402
from entertainment.models import Books, Movies, Users  # noqa: E402
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
    db = TestingSessionLocal()
    db.execute(text("DELETE FROM users"))
    db.execute(text("DELETE FROM movies"))
    db.execute(text("DELETE FROM books"))
    db.commit()
    db.close()


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
        # "first_name": None,
        # "last_name": None,
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


@pytest.fixture
def mock_get_movies_genres():
    with patch(
        "entertainment.routers.movies.get_movies_genres"
    ) as mock_get_movies_genres:
        mock_get_movies_genres.return_value = list(
            map(lambda genre: genre.value, MovieGenres)
        )
        yield mock_get_movies_genres


@pytest.fixture()
async def added_movie(
    async_client: AsyncClient, created_token: str, mock_get_movies_genres
) -> dict:
    """Creates movie record in the database before running a test."""
    payload = {
        "title": "Nigdy w życiu!",
        "premiere": "2004-02-13",
        "score": 6.2,
        "genres": ["comedy", "romance"],
        "overview": "Judyta po rozwodzie zaczyna budowę domu pod Warszawą i znajduje nową miłość.",
        "crew": "Danuta Stenka, Judyta Kozłowska, Joanna Brodzik, Ula, Artur Żmijewski, Adam, Jan Frycz, Tomasz Kozłowski",
        "orig_title": "Nigdy w życiu!",
        "orig_lang": "Polish",
        "budget": None,
        "revenue": None,
        "country": "PL",
    }
    await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    movie = (
        TestingSessionLocal()
        .query(Movies)
        .filter(Movies.title == "Nigdy w życiu!")
        .first()
    )
    return jsonable_encoder(movie)


@pytest.fixture
def mock_get_books_genres():
    with patch("entertainment.routers.books.get_books_genres") as mock_get_books_genres:
        mock_get_books_genres.return_value = [
            "Classics",
            "Fantasy",
            "Fiction",
            "Magic",
            "Psychology",
        ]
        yield mock_get_movies_genres


@pytest.fixture()
async def added_book(
    async_client: AsyncClient, created_token: str, mock_get_books_genres
) -> dict:
    """Creates book record in the database before running a test."""
    payload = {
        "title": "New book",
        "author": "John Doe",
        "description": None,
        "genres": ["classics", "romance"],
        "avg_rating": 3.2,
        "num_ratings": 1000,
        "first_published": "2011-11-11",
    }
    await async_client.post(
        "/books/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    book = TestingSessionLocal().query(Books).filter(Books.title == "New book").first()
    return jsonable_encoder(book)
