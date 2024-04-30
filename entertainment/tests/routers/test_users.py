import os

import pytest
from httpx import AsyncClient

from entertainment.database import get_db  # noqa
from entertainment.main import app  # noqa
from entertainment.models import Users  # noqa
from entertainment.routers.auth import create_access_token, get_current_user  # noqa
from entertainment.routers.users import get_logged_in_user  # noqa
from entertainment.tests.conftest import (  # noqa
    TestingSessionLocal,
    check_if_db_users_table_is_empty,
    create_db_user,
    create_user_and_token,
    mock_authorisation,
)

os.environ["ENV_STATE"] = "test"

import logging  # noqa

logger = logging.getLogger(__name__)

COMMEND = "pytest --disable-warnings --log-cli-level=DEBUG -s"


@pytest.mark.anyio
async def test_create_user_201(async_client: AsyncClient):
    """Test creating a new user is successfull."""
    request_data = {
        "username": "deadpool",
        "email": "deadpool@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = await async_client.post("/user/register", json=request_data)

    logger.debug("\nTEST - response.text: %s" % response.text)

    assert response.status_code == 201
    assert "deadpool@example.com" in response.text
    assert "deadpool" in response.json()["username"]


@pytest.mark.anyio
async def test_create_user_201_with_fixture(registered_user: dict):
    """Test creating a new user with fixture is successfull."""
    user = registered_user
    assert "testuser" in user["username"]
    assert (
        TestingSessionLocal().query(Users).filter(Users.username == "testuser").first()
        is not None
    )


@pytest.mark.anyio
async def test_create_user_400_with_not_unique_username(
    async_client: AsyncClient, created_user
):
    """Test creating a new user rejected if username already taken."""
    user_in_db = created_user
    request_data = {
        "username": user_in_db.username,
        "email": "deadpool@example.com",
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = await async_client.post("/user/register", json=request_data)

    assert response.status_code == 400
    assert "A user with that username already exists" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_user_400_with_not_unique_email(
    async_client: AsyncClient, created_user
):
    """Test creating a new user rejected if email is already taken."""
    user_in_db = created_user
    request_data = {
        "username": "deadpool",
        "email": user_in_db.email,
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = await async_client.post("/user/register", json=request_data)

    assert response.status_code == 400
    assert "A user with that email already exists" in response.json()["detail"]


@pytest.mark.anyio
async def test_create_user_400_with_incorrect_password(async_client: AsyncClient):
    """Test creating a new user rejected passwords does not match."""
    request_data = {
        "username": "deadpool",
        "email": "deadpool@example.com",
        "password": "deadpool123",
        "confirm_password": "wrongstring",
    }
    response = await async_client.post("/user/register", json=request_data)

    assert response.status_code == 400
    assert "Passwords does not match" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_logged_in_user_200_if_authenticated(
    registered_user: dict, created_user_token: str, async_client: AsyncClient
):
    """Test access to current user data successfull with authentication."""
    # Creating a user in db (can be skipped, as a created_user_token fixture has it embedded)
    user = registered_user

    # Creating a token for a user
    token = created_user_token

    # Getting logged in user data with token authorization
    response = await async_client.get(
        "/user/", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert user["username"] in response.content.decode()


@pytest.mark.anyio
async def test_get_logged_in_user_401_if_not_authenticated(async_client: AsyncClient):
    """Test access to current user forbidden without user authentication."""
    response = await async_client.get("/user/")
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_get_user_200_with_auth_user(
    async_client: AsyncClient, registered_user: dict, created_user_token: str
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the same user."""
    # Creating a 'testuser'
    user = registered_user

    # Creating a token for a user
    token = created_user_token

    # Calling the endpoint for 'testuser' with 'testuser' authenticated
    response = await async_client.get(
        "/user/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert user["username"] in response.json()["username"]
    # assert logged_in_user.json()["username"] == "admin_user"
    # assert logged_in_user.json()["role"] == "admin"
    # logger.debug("\nTEST - <logged in user>: %s" % logged_in_user.json())


@pytest.mark.anyio
async def test_get_user_with_other_username_200_with_admin_auth(
    registered_user: dict, async_client: AsyncClient
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the another user with admin role."""
    # Creating a 'testuser'
    testuser = registered_user

    # Creating admin_user and token for an admin_user
    admin_token = create_user_and_token(
        username="admin_user",
        email="admin@example.com",
        password="password",
        role="admin",
    )

    # Endpoint call for 'testuser' with authentication of 'admin_user'
    response = await async_client.get(
        "/user/testuser", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert testuser["username"] == response.json()["username"]


@pytest.mark.anyio
async def test_get_user_401_if_not_authenticated(async_client: AsyncClient):
    """Test access to user 'testuser' forbidden without user authentication."""
    response = await async_client.get("/user/testuser")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


@pytest.mark.anyio
async def test_get_user_404_if_user_not_found(
    async_client: AsyncClient, created_user_token: str
):
    """Test access to user 'someuser' not found if someuser not in db."""
    # Creating testuser and token for the testuser
    token = created_user_token

    # Calling the endpoint for 'someuser' with 'testuser' authenticated
    response = await async_client.get(
        "/user/someuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    msg = "User 'someuser' not found in the database."
    assert msg in response.content.decode()


@pytest.mark.anyio
async def test_get_user_with_other_username_403_with_no_amin_auth(
    async_client: AsyncClient, registered_user: dict
):
    """Test accessing existing user 'testuser' forbidden with authentication
    of the another user without admin role."""
    # Creating a 'testuser'
    testuser = registered_user

    # Creating no_admin_user and token for an no_admin_user
    no_admin_token = create_user_and_token(
        username="simple_user",
        email="simple@example.com",
        password="password",
        role="user",
    )

    # Endpoint call for 'testuser' with authentication of 'non_admin_user'
    response = await async_client.get(
        "/user/testuser",
        headers={"Authorization": f"Bearer {no_admin_token}"},
    )
    assert response.status_code == 403
    msg = "Permission denied. Access to see other users' data is restricted."
    assert msg == response.json()["detail"]
