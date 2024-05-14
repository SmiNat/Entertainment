import logging

import pytest
from httpx import AsyncClient

from entertainment.models import Users
from entertainment.routers.auth import bcrypt_context
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_users import create_user_and_token

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
    # Creating a user with registered_user fixture
    user = registered_user
    assert "testuser" in user["username"]
    assert (
        TestingSessionLocal().query(Users).filter(Users.username == "testuser").first()
        is not None
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "username, email, error_msg, comment",
    [
        (
            "testuser",
            "deadpool@example.com",
            "A user with that username already exists",
            "not unique username",
        ),
        (
            "TestUser",
            "deadpool@example.com",
            "UNIQUE constraint failed: index 'idx_user_lowercased_username'",
            "not unique username - index set on case sensitive uniqueness",
        ),
        (
            "deadpool",
            "test@example.com",
            "A user with that email already exists",
            "not unique email",
        ),
    ],
)
async def test_create_user_400_with_not_unique_data(
    async_client: AsyncClient,
    registered_user: dict,
    username: str,
    email: str,
    error_msg: str,
    comment: str,
):
    """Test creating a new user rejected if username already taken."""
    # Calling the endpoint with invalid payload
    payload = {
        "username": username,
        "email": email,
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = await async_client.post("/user/register", json=payload)

    assert response.status_code == 400
    assert error_msg in response.json()["detail"]


@pytest.mark.anyio
async def test_create_user_400_with_unmatched_password(async_client: AsyncClient):
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
    created_user_token: tuple, async_client: AsyncClient
):
    """Test access to current user data successfull with authentication."""
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Getting logged in user data with token authorization
    response = await async_client.get(
        "/user/current", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert user["username"] in response.content.decode()


@pytest.mark.anyio
async def test_get_logged_in_user_401_if_not_authenticated(async_client: AsyncClient):
    """Test access to current user forbidden without user authentication."""
    response = await async_client.get("/user/current")
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_get_user_200_if_authenticated(
    async_client: AsyncClient, created_user_token: tuple
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the same user."""
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Calling the endpoint for 'testuser' with 'testuser' authenticated
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert user["username"] in response.json()["username"]


@pytest.mark.anyio
async def test_get_user_with_other_username_200_with_admin_auth(
    registered_user: dict, async_client: AsyncClient
):
    """Test accessing existing user 'testuser' successfull with authentication
    of the another user with admin role."""
    # Creating a 'testuser'
    testuser = registered_user

    # Creating 'admin_user' and token for an admin_user
    admin_user, admin_token = create_user_and_token(
        username="admin_user",
        email="admin@example.com",
        password="password",
        role="admin",
    )

    # Endpoint call for 'testuser' with authentication of 'admin_user'
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert testuser["username"] == response.json()["username"]


@pytest.mark.anyio
async def test_get_user_401_if_not_authenticated(async_client: AsyncClient):
    """Test access to user 'testuser' forbidden without user authentication."""
    response = await async_client.get("/user/check/testuser")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


@pytest.mark.anyio
async def test_get_user_404_if_user_not_found(
    async_client: AsyncClient, created_user_token: tuple
):
    """Test access to user 'someuser' not found if someuser not in db."""
    # Creating 'testuser' and a token for the 'testuser'
    user, token = created_user_token

    # Calling the endpoint for 'someuser' with 'testuser' authenticated
    response = await async_client.get(
        "/user/check/someuser", headers={"Authorization": f"Bearer {token}"}
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
    testuser = registered_user  # noqa

    # Creating 'no_admin_user' and a token for an no_admin_user
    user, no_admin_token = create_user_and_token(
        username="simple_user",
        email="simple@example.com",
        password="password",
        role="user",
    )

    # Endpoint call for 'testuser' with authentication of 'non_admin_user'
    response = await async_client.get(
        "/user/check/testuser",
        headers={"Authorization": f"Bearer {no_admin_token}"},
    )
    assert response.status_code == 403
    msg = "Permission denied. Access to see other users' data is restricted."
    assert msg == response.json()["detail"]


@pytest.mark.anyio
async def test_update_user_204(async_client: AsyncClient, registered_user: dict):
    # Creating a 'testuser'
    user = registered_user

    # Creating a token for a 'testuser'
    response = await async_client.post(
        "/auth/token", data={"username": user["username"], "password": "testpass123"}
    )
    token = response.json()["access_token"]

    # Getting the logged in user data
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    original_user = response.json()
    assert user["username"] in original_user["username"]
    assert original_user["email"] == "test@example.com"
    assert original_user["first_name"] is None
    assert original_user["last_name"] is None
    assert original_user["id"] == 1

    # Calling the update_user endpoint for 'testuser'
    payload = {
        "email": None,
        "first_name": "John",
        "last_name": "Doe",
    }
    response = await async_client.patch(
        "/user/update", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Token for updated user has not changed (the same username)
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    current_user = response.json()
    assert current_user["username"] == "testuser"
    assert current_user["email"] == "test@example.com"
    assert current_user["first_name"] == "John"
    assert current_user["last_name"] == "Doe"
    assert current_user["id"] == 1


@pytest.mark.anyio
async def test_update_user_401_if_not_authenticated(async_client: AsyncClient):
    # Calling the update_user endpoint without user authentication
    payload = {
        "email": None,
        "first_name": "John",
        "last_name": "Doe",
    }
    response = await async_client.patch("/user/update", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_update_user_400_email_already_taken(
    async_client: AsyncClient, created_user_token: tuple
):
    # Creating some other user
    other_user = {
        "username": "otheruser",
        "email": "other@example.com",
        "password": "password",
        "confirm_password": "password",
    }
    response = await async_client.post("/user/register", json=other_user)
    assert response.status_code == 201

    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Getting the logged in user data (to verify email address for logged in user)
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert user["username"] in response.json()["username"]
    assert response.json()["email"] == "test@example.com"

    # Calling the update_user endpoint for 'testuser' with attempt to change
    # the email to already taken one
    payload = {
        "email": other_user["email"],
        "first_name": "John",
        "last_name": "Doe",
    }
    response = await async_client.patch(
        "/user/update", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "UNIQUE constraint failed: users.email" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_email",
    [("invalid"), ("invalid@"), ("@invalid"), ("sth@invalid")],
)
async def test_update_user_422_email_invalid(
    async_client: AsyncClient, created_user_token: tuple, invalid_email
):
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Getting the logged in user data
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    original_user = response.json()
    assert user["username"] in original_user["username"]
    assert original_user["email"] == "test@example.com"

    # Calling the update_user endpoint for 'testuser' with already taken email
    payload = {
        "email": invalid_email,
        "first_name": "John",
        "last_name": "Doe",
    }
    response = await async_client.patch(
        "/user/update", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422
    assert "value is not a valid email address" in response.text


@pytest.mark.anyio
async def test_delete_user_204(async_client: AsyncClient, created_user_token: tuple):
    # Creating a 'testuser' and a token for a 'testuser'
    testuser, testuser_token = created_user_token

    # Creating 'admin_user' and token for an 'admin_user'
    admin_user, admin_token = create_user_and_token(
        username="admin_user",
        email="admin@example.com",
        password="password",
        role="admin",
    )

    # Veryfying if the 'testuser' can be found in db with authentication of 'admin_user'
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert testuser["username"] == response.json()["username"]

    # Calling delete_user endpoint by the 'testuser' (deleting 'testuser')
    response = await async_client.delete(
        "/user/delete", headers={"Authorization": f"Bearer {testuser_token}"}
    )
    assert response.status_code == 204

    # Veryfying if the deleted user can be found in db with authentication of 'admin_user'
    response = await async_client.get(
        "/user/check/testuser", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert "User 'testuser' not found in the database." in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_user_401_if_not_authenticated(async_client: AsyncClient):
    # Calling the delete_user endpoint without authentication
    response = await async_client.delete("/user/delete")
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_change_password_204(
    created_user_token: tuple, async_client: AsyncClient
):
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Calling change_password endpoint with new password
    payload = {
        "current_password": "testpass123",
        "new_password": "password",
        "confirm_password": "password",
    }
    response = await async_client.put(
        "/user/password", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Check if the password has been changed in the database
    with TestingSessionLocal() as db:
        # Get the user from the database
        user = db.query(Users).filter(Users.id == user["id"]).first()
        assert user is not None

        # Verify that the new password matches
        assert bcrypt_context.verify(payload["new_password"], user.hashed_password)


@pytest.mark.anyio
async def test_change_password_401_if_not_authenticated(async_client: AsyncClient):
    # Calling the change_password endpoint
    payload = {
        "current_password": "testpass123",
        "new_password": "password",
        "confirm_password": "password",
    }
    response = await async_client.put("/user/password", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_change_password_401_if_invalid_current_password(
    created_user_token: tuple, async_client: AsyncClient
):
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Calling change_password endpoint with incorrect old password
    payload = {
        "current_password": "incorrect_password",
        "new_password": "password",
        "confirm_password": "password",
    }
    response = await async_client.put(
        "/user/password", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert (
        "Failed Authentication - incorrect current password"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_change_password_400_if_passwords_not_match(
    created_user_token: tuple, async_client: AsyncClient
):
    # Creating a 'testuser' and a token for a 'testuser'
    user, token = created_user_token

    # Calling change_password endpoint with new passwords (unmatch)
    payload = {
        "current_password": "testpass123",
        "new_password": "password_111",
        "confirm_password": "password_999",
    }
    response = await async_client.put(
        "/user/password", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Passwords do not match" in response.json()["detail"]
