import logging
import os

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.orm import Session

from entertainment.exceptions import CredentialsException
from entertainment.routers.auth import (
    access_token_expire_minutes,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_users import create_db_user

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
    # Creating a user: registered_user fixture
    # Calling authenticate_user funcion
    user = authenticate_user(
        registered_user["username"], "testpass123", TestingSessionLocal()
    )
    # Verifying if authenticated user == to a registred user
    assert user.email == registered_user["email"]


def test_authenticate_user_username_not_found_raises_404():
    # Calling authenticate_user funcion with non existing user
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user("fake_username", "testpass123", TestingSessionLocal())
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 404
    assert "User 'fake_username' not found in the database" in exc_info.value.detail


@pytest.mark.anyio
async def test_authenticate_user_incorrect_password_raises_401(registered_user: dict):
    # Creating a user: registered_user fixture (with password: testpass123)
    # Calling authenticate_user funcion with incorrect password
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user(
            registered_user["username"], "fake_password", TestingSessionLocal()
        )
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 401
    assert "Failed Authentication - incorrect password" in exc_info.value.detail


@pytest.mark.anyio
async def test_get_current_user_successful(db_session: Session):
    # Createing a user
    create_db_user()
    # Creating token for a user
    token = create_access_token("testuser", 1, "user")
    # Verifying get_current_user response
    response = await get_current_user(db_session, token)
    assert {"username": "testuser", "id": 1, "role": "user"}.items() == response.items()


@pytest.mark.anyio
async def test_get_current_user_user_not_in_db(caplog, db_session: Session):
    # Creating token for a user
    token = create_access_token("testuser", 1, "user")
    # Verifying get_current_user response
    with pytest.raises(CredentialsException) as exc_info:
        with caplog.at_level("DEBUG"):
            await get_current_user(db_session, token)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials." in exc_info.value.detail
    assert "No user 'testuser' in DB or user has inactive status" in caplog.text


@pytest.mark.anyio
async def test_get_current_inactive_user(caplog, db_session: Session):
    # Createing a user with inactive account
    create_db_user(is_active=False)
    # Creating token for a user
    token = create_access_token("testuser", 1, "user")
    # Verifying get_current_user response
    with pytest.raises(CredentialsException) as exc_info:
        with caplog.at_level("DEBUG"):
            await get_current_user(db_session, token)
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials." in exc_info.value.detail
    assert "No user 'testuser' in DB or user has inactive status" in caplog.text


@pytest.mark.anyio
async def test_get_current_user_expired_token_raises_401(mocker, db_session: Session):
    # Populating db with a user
    create_db_user()
    # Mocking access_token_expire_minutes function (to create a token which is already expired)
    mocker.patch(
        "entertainment.routers.auth.access_token_expire_minutes", return_value=-1
    )
    # Creating expired token
    token = create_access_token("testuser", 1, "user")
    # Calling get_current_user funcion with expired token
    with pytest.raises(CredentialsException) as exc_info:
        await get_current_user(db_session, token)
    assert exc_info.value.status_code == 401
    assert "Token has expired" in exc_info.value.detail


@pytest.mark.anyio
@pytest.mark.parametrize(
    "username, user_id, user_role",
    [(None, 1, "user"), ("testuser", None, "admin"), ("testuser", 1, None)],
)
async def test_get_current_user_invalid_credentials_raises_401(
    username, user_id, user_role, db_session
):
    # Populating db with a user
    create_db_user()
    # Creating token with invalid data
    token = create_access_token(username, user_id, user_role)
    # Calling get_current_user funcion with invalid token
    with pytest.raises(CredentialsException) as exc_info:
        await get_current_user(db_session, token)
    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


@pytest.mark.anyio
async def test_login_for_access_token(async_client: AsyncClient, registered_user: dict):
    # Creating a user: registered_user fixture
    # Calling login_for_access_token function
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
async def test_login_for_access_token_404_with_non_existing_user(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/auth/token", data={"username": "fake_user", "password": "password"}
    )
    assert response.status_code == 404
