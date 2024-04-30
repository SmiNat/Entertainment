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
async def test_get_user_401_if_not_authenticated(async_client: AsyncClient):
    """Test access to user 'testuser' forbidden without user authentication."""
    response = await async_client.get("/user/testuser")
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()  # remove !!!
    assert "Not authenticated" in response.text  # remove !!!
    assert "Not authenticated" == response.json()["detail"]  # remove !!!


@pytest.mark.anyio
async def test_get_user_404_if_not_found(async_client: AsyncClient):
    """Test access to user 'testuser' not found if testuser not in db."""
    check_if_db_users_table_is_empty()

    # Verifying if there is no authenticated user
    logged_in_user = await async_client.get("/user/")
    assert logged_in_user.status_code == 401

    # Mocking authorisation for a 'testuser'
    mock_authorisation(username="testuser", id=1, role="admin")
    # Veryfying if 'testuser' was successfully authenticated
    logged_in_user = await async_client.get("/user/")
    assert logged_in_user.status_code == 200
    assert logged_in_user.json()["username"] == "testuser"
    logger.debug("\nTEST - <logged in user>: %s" % logged_in_user.json())

    # Calling the endpoint for 'someuser' with 'testuser' authenticated
    response = await async_client.get("/user/someuser")
    assert response.status_code == 404
    msg = "User 'someuser' not found in the database."
    assert msg in response.content.decode()


@pytest.mark.anyio
async def test_get_user_200_with_auth_user(
    async_client: AsyncClient,
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the same user."""
    check_if_db_users_table_is_empty()

    # Creating a 'testuser'
    user = create_db_user("testuser", "test@example.com", "password")

    # Mocking authorisation for a 'testuser'
    mock_authorisation(user=user)
    # Veryfying if 'testuser' was successfully authenticated
    logged_in_user = await async_client.get("/user/")
    assert logged_in_user.status_code == 200
    assert logged_in_user.json()["username"] == "testuser"
    logger.debug("\nTEST - <logged in user>: %s" % logged_in_user.json())

    # Calling the endpoint for 'testuser' with 'testuser' authenticated
    response = await async_client.get("/user/testuser")
    assert response.status_code == 200
    assert logged_in_user.json()["username"] == "testuser"


@pytest.mark.anyio
async def test_get_user_with_other_username_200_with_admin_auth(
    async_client: AsyncClient,
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the another user with admin role."""
    check_if_db_users_table_is_empty()

    # Creating a 'testuser'
    testuser = create_db_user("testuser", "test@example.com", "password", "user")

    # Mocking authorisation for a admin_user...
    mock_authorisation(username="admin_user", id=2, role="admin")
    # Veryfying if 'admin_user' was successfully authenticated
    logged_in_user = await async_client.get("/user/")
    assert logged_in_user.status_code == 200
    assert logged_in_user.json()["username"] == "admin_user"
    assert logged_in_user.json()["role"] == "admin"
    logger.debug("\nTEST - <logged in user>: %s" % logged_in_user.json())

    # Endpoint call for 'testuser' with authentication of 'admin_user'
    response = await async_client.get(f"/user/{testuser.username}")
    assert response.status_code == 200
    assert testuser.username == response.json()["username"]


@pytest.mark.anyio
async def test_get_user_with_other_username_403_with_no_amin_auth(
    async_client: AsyncClient,
):
    """Test accessing existing user 'test_user' forbidden with authentication
    of the another user without admin role."""
    check_if_db_users_table_is_empty()

    # Creating a 'testuser'
    testuser = create_db_user("testuser", "test@example.com", "password", "user")

    # Mocking authorisation for a non_admin_user...
    mock_authorisation(username="non_admin_user", id=2, role="user")
    # Veryfying if 'non_admin_user' was successfully authenticated
    logged_in_user = await async_client.get("/user/")
    assert logged_in_user.status_code == 200
    assert logged_in_user.json()["username"] == "non_admin_user"
    assert logged_in_user.json()["role"] == "user"
    logger.debug("\nTEST - <logged in user>: %s" % logged_in_user.json())

    # Endpoint call for 'testuser' with authentication of 'non_admin_user'
    response = await async_client.get(f"/user/{testuser.username}")
    assert response.status_code == 403
    msg = "Permission denied. Access to see other users' data is restricted."
    assert msg == response.json()["detail"]
