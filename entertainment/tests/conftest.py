import logging
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import MetaData, create_engine, text  # noqa
from sqlalchemy.orm import declarative_base, sessionmaker  # noqa

os.environ["ENV_STATE"] = "test"

from entertainment.config import config  # noqa: E402
from entertainment.database import Base, get_db  # noqa
from entertainment.exceptions import DatabaseNotEmptyError  # noqa: E402
from entertainment.main import app  # noqa: E402
from entertainment.models import Movies, Users  # noqa
from entertainment.routers.auth import (  # noqa: E402
    create_access_token,
    get_current_user,
)

logger = logging.getLogger(__name__)

# Creating test.db database instead of using application db (entertainment.db)
engine = create_engine(
    config.DATABASE_URL,  # test.db
    connect_args={"check_same_thread": False},
    echo=False,
)

Base.metadata.drop_all(bind=engine)
# Base.metadata.drop_all(bind=engine, tables=[Users.__table__], checkfirst=True)
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
    async with AsyncClient(app=app, base_url=client.base_url) as ac:
        yield ac


# Some helpful functions to use in tests
def create_db_user(
    username: str,
    email: str,
    hashed_password: str,
    role: str = "user",
    is_active: bool = True,
    first_name: str | None = None,
    last_name: str | None = None,
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


def mock_authorisation(
    user: Users | dict = None, username: str = None, id: int = None, role: str = "user"
):
    if isinstance(user, Users):
        app.dependency_overrides[get_current_user] = lambda: {
            "username": user.username,
            "id": user.id,
            "role": user.role,
        }
    elif isinstance(user, dict):
        app.dependency_overrides[get_current_user] = lambda: {
            "username": user["username"],
            "id": user["id"],
            "role": user["role"],
        }
    elif user and not isinstance(user, (Users, dict)):
        raise AttributeError(
            "'user' parameter must be of Users instance or a dictionary, not {}.".format(
                type(user)
            )
        )
    if not user:
        if not username or not id:
            raise AttributeError(
                "Either 'user' parameter is required or parameters: 'username' and 'id'."
            )
        app.dependency_overrides[get_current_user] = lambda: {
            "username": username,
            "id": id,
            "role": role,
        }


def check_if_db_users_table_is_empty():
    db = TestingSessionLocal()
    db_content = db.query(Users).all()
    if db_content:
        logger.warning(
            "Database warning: not empty Users table; %s"
            % [
                {"username": element.username, "id": element.id, "role": element.role}
                for element in db_content
            ]
        )
        raise DatabaseNotEmptyError("Users table not empty.")


def create_user_token(username: str, email: str, password: str, role: str = "user"):
    user = create_db_user(username, email, password, role)
    mock_authorisation(user)
    token = create_access_token(user.username, user.id, user.role)
    return token


# Some app fixtures to use in tests
@pytest.fixture
async def registered_user(async_client: AsyncClient) -> dict:
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        # "first_name": None,
        # "last_name": None,
        # "role": "user",
        "password": "testpass123",
        "confirm_password": "testpass123",
    }
    user = await async_client.post("/user/register", json=payload)
    # user = async_client.post("/user", params="testuser")
    return user.json()


@pytest.fixture
async def created_user_token(async_client, created_user) -> dict:
    user = created_user
    token = create_access_token(
        username=user["username"],
        user_id=user["id"],
        role=user["role"],
    )
    return token
