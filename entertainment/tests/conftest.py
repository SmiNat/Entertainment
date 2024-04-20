import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text  # noqa
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["ENV_STATE"] = "test"

from entertainment.config import config  # noqa
from entertainment.database import Base, get_db  # noqa
from entertainment.main import app  # noqa
from entertainment.routers.auth import bcrypt_context, get_current_user  # noqa
from entertainment.routers.users import create_user, CreateUser  # noqa
from entertainment.routers.movies import add_movie, MoviesRequest  # noqa
from entertainment.models import Users, Movies  # noqa


# TEST_DATABASE_URL = "sqlite:///./tests/test.db"

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


# Overriding database connection for the endpoins
def override_get_db():
    """Sets a clean db session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.execute(text("DELETE FROM users"))
        db.execute(text("DELETE FROM movies"))
        db.commit()
        db.close()


app.dependency_overrides[get_db] = override_get_db


# @pytest.fixture
# def clean_db():
#     db = TestingSessionLocal()
#     db.execute(text("DELETE FROM users"))
#     db.execute(text("DELETE FROM movies"))
#     db.commit()
#     db.close()


def override_get_current_user():
    # return {"username": "testuser", "id": str(uuid.uuid4()), "role": "admin"}
    return {"username": "testuser", "id": 1, "role": "admin"}


app.dependency_overrides[get_current_user] = override_get_current_user


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
# async def create_dummy_user():
#     db = next(override_get_db())
#     user = Users(
#         # id=uuid.uuid4(),
#         # id=1,
#         username="testuser",
#         email="test@example.com",
#         first_name="Test",
#         last_name="User",
#         hashed_password=bcrypt_context.hash("testpass123"),
#         role="admin",
#         is_active=True,
#     )
#     db.add(user)
#     db.commit()

#     yield


#     # db.query(Users).filter(Users.username == "testuser").delete()
#     # db.commit()


# @pytest.fixture
# def test_user():
#     user = Users(
#         id=uuid.uuid4(),
#         username="testuser",
#         email="test@example.com",
#         first_name="Test",
#         last_name="User",
#         hashed_password=bcrypt_context.hash("testpass123"),
#         role="admin",
#         is_active=True,
#     )

#     db = TestingSessionLocal()
#     db.add(user)
#     db.commit()
#     yield user
#     db.execute(text("DELETE FROM users;"))
#     db.commit()
#     # with engine.connect() as connection:
#     #     connection.execute(text("DELETE FROM users;"))
#     #     connection.commit()


# # Creating app fixtures
# @pytest.fixture
# async def created_user(async_client: AsyncClient) -> dict:
#     payload = {
#         "username": "testuser",
#         "email": "test@example.com",
#         "password": "testpass123",
#         "confirm_password": "testpass123",
#     }
#     await async_client.post("/user/register", json=payload)
#     # user = async_client.post("/user", params="testuser")
#     # return user


# # @pytest.fixture()
# # async def create_db_records(async_client: AsyncClient):
# #     movie = {"title": "Test movie", "premiere": "2024-1-1", "score": 9, "genres": ["action", "drama"]}
