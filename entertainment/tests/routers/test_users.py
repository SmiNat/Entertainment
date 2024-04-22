import os

import pytest

from entertainment.main import app  # noqa
from entertainment.models import Users  # noqa
from entertainment.routers.auth import create_access_token, get_current_user  # noqa
from entertainment.tests.conftest import TestingSessionLocal, create_db_user  # noqa

os.environ["ENV_STATE"] = "test"

import logging  # noqa

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_user_201(client):
    """Test creating a new user is successfull."""
    request_data = {
        "username": "deadpool",
        "email": "deadpool@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = client.post("/user/register", json=request_data)

    logger.debug("test_create_user - response.text: %s" % response.text)

    assert response.status_code == 201
    assert "deadpool@example.com" in response.text
    assert "deadpool" in response.json()["username"]


@pytest.mark.anyio
async def test_get_user_401_if_not_authenticated(async_client):
    """Test access to user 'testuser' forbidden without user authentication."""
    response = await async_client.get("/user/testuser")
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()  # remove !!!
    assert "Not authenticated" in response.text  # remove !!!


@pytest.mark.anyio
async def test_get_user_200_with_auth_user(async_client):
    """Test accessing existing user 'test_user' successfull with authentication
    of the same user."""
    # Creating a 'test_user'
    user = create_db_user("test_user", "test@example.com", "password")

    # Mocking authorisation for a user...
    app.dependency_overrides[get_current_user] = lambda: {
        "username": user.username,
        "id": user.id,
        "role": user.role,
    }

    # Creating a token for a user
    token = create_access_token(username=user.username, user_id=user.id, role=user.role)

    # Endpoint call with user token authentication
    response = await async_client.get(
        "/user/test_user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


@pytest.mark.anyio
async def test_get_user_with_other_username_200_with_admin_auth(async_client):
    """Test accessing existing user 'john_doe' successfull with authentication
    of the another user with admin role."""
    # Creating a 'test_user' and 'admin_user'
    test_user = create_db_user("test_user", "test@example.com", "password", "user")
    admin_user = create_db_user("admin_user", "admin@example.com", "password", "admin")

    # Creating a token for 'admin_user'
    token = create_access_token(
        username=admin_user.username, user_id=admin_user.id, role=admin_user.role
    )

    # Endpoint call for 'test_user' with authentication of 'admin_user'
    response = await async_client.get(
        f"/user/{test_user.username}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert test_user.username == response.json()["username"]


@pytest.mark.anyio
async def test_get_user_with_other_username_403_with_no_amin_auth(async_client):
    """Test accessing existing user 'john_doe' forbidden with authentication
    of the another user without admin role."""
    print("====================================")
    # Creating a 'test_user' and 'admin_user'
    test_user = create_db_user("test_user", "test@example.com", "password", "user")
    other_user = create_db_user("other_user", "user@example.com", "password", "user")

    # Creating a token for 'admin_user'
    token = create_access_token(
        username=other_user.username, user_id=other_user.id, role=other_user.role
    )

    db = TestingSessionLocal()
    for user in db.query(Users).all():
        print(">>>>>>>>>>>>>", user.username)

    # Endpoint call for 'test_user' with authentication of 'other_user'
    response = await async_client.get(
        f"/user/{test_user.username}",
        headers={"Authorization": f"Bearer {token}"},
    )
    print("====================================")
    assert response.status_code == 403
    msg = "Permission denied. Access to see other users' data is restricted"
    assert msg == response.content.decode()


@pytest.mark.anyio
async def test_get_user_not_found(
    async_client, use_authenticated_admin_user, create_test_admin_user
):
    # test_user = create_test_user
    # print(">>>>>>>>>>>>>>", test_user.id, test_user.username)
    # user_access_token = create_access_token(
    #     username=test_user.username, user_id=test_user.id, role=test_user.role
    # )
    response = await async_client.get(
        "/user/testuser",
        # headers={"Authorization": f"Bearer {user_access_token}"}
    )
    assert response.status_code == 200, response.text

    # response = await async_client.get(
    #     "/user/deadpool", headers={"Authorization": f"Bearer {user_access_token}"}
    # )
    # assert response.status_code == 404, response.text


# @pytest.mark.asyncio
# async def test_get_user_200(create_dummy_user):
#     user = create_dummy_user
#     user_access_token = create_access_token(
#         username="test@example.com", user_id=1, role="admin"
#     )
#     response = client.get(
#         "/user/testuser", headers={"Authorization": f"Bearer {user_access_token}"}
#     )
#     assert response.status_code == 200, response.text
#     data = response.json()
#     assert data["email"] == user.email == "test@example.com"
#     assert data["id"] == str(user.id)


# @pytest.mark.anyio
# async def test_get_user(async_client):
#     user_access_token = create_access_token(
#         username="test@example.com", user_id=1, role="admin"
#     )
#     response = await async_client.get(
#         "/user/testuser", headers={"Authorization": f"Bearer {user_access_token}"}
#     )
#     assert response.status_code == 200
