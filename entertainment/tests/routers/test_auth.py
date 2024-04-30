import os

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from jose import jwt

from entertainment.exceptions import CredentialsException
from entertainment.routers.auth import (
    access_token_expire_minutes,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from entertainment.tests.conftest import TestingSessionLocal

os.environ["ENV_STATE"] = "test"

import logging  # noqa

logger = logging.getLogger(__name__)


def test_access_token_expire_minutes():
    assert access_token_expire_minutes() == 30


def test_create_access_token():
    token = create_access_token("testuser", 1, "user")
    assert {"sub": "testuser", "id": 1, "role": "user"}.items() <= jwt.decode(
        token,
        key=str(os.environ.get("SECRET_KEY")),
        algorithms=[os.environ.get("ALGORITHM")],
    ).items()


@pytest.mark.anyio
async def test_authenticate_user(registered_user: dict):
    user = authenticate_user(
        registered_user["username"], "testpass123", TestingSessionLocal()
    )
    assert user.email == registered_user["email"]


@pytest.mark.anyio
async def test_authenticate_user_username_not_found(registered_user: dict):
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user("fake_username", "testpass123", TestingSessionLocal())
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 404
    assert "User 'fake_username' not found in the database" in exc_info.value.detail


@pytest.mark.anyio
async def test_authenticate_user_incorrect_password(registered_user: dict):
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user(
            registered_user["username"], "fake_password", TestingSessionLocal()
        )
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 401
    assert "Failed Authentication - incorrect password" in exc_info.value.detail


@pytest.mark.anyio
async def test_get_current_user():
    token = create_access_token("testuser", 1, "user")
    response = await get_current_user(token)
    assert {"username": "testuser", "id": 1, "role": "user"}.items() == response.items()


@pytest.mark.anyio
async def test_get_current_user_expired_token(mocker):
    mocker.patch(
        "entertainment.routers.auth.access_token_expire_minutes", return_value=-1
    )
    token = create_access_token("testuser", 1, "user")
    with pytest.raises(CredentialsException) as exc_info:
        await get_current_user(token)
    assert exc_info.value.status_code == 401
    assert "Token has expired" in exc_info.value.detail


@pytest.mark.anyio
@pytest.mark.parametrize(
    "username, user_id, user_role",
    [(None, 1, "user"), ("testuser", None, "admin"), ("testuser", 1, None)],
)
async def test_get_current_user_invalid_credentials(username, user_id, user_role):
    token = create_access_token(username, user_id, user_role)
    with pytest.raises(CredentialsException) as exc_info:
        await get_current_user(token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.anyio
async def test_login_user(async_client: AsyncClient, registered_user: dict):
    response = await async_client.post(
        "/auth/token",
        data={
            "username": registered_user["username"],
            "password": "testpass123",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json().keys()
    assert "bearer" in response.json()["token_type"]


@pytest.mark.anyio
async def test_login_user_not_exists(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/token", data={"username": "fake_user", "password": "password"}
    )
    assert response.status_code == 404
