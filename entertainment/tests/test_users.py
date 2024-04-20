import os

import pytest

from entertainment.routers.auth import create_access_token

os.environ["ENV_STATE"] = "test"

import logging  # noqa


logger = logging.getLogger(__name__)

# test_db = "./tests/test.db"

# create_db(test_db)

# SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"
# SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./tests/test.db"

# engine = create_sqlite_engine(SQLALCHEMY_TEST_DATABASE_URL)

# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base.metadata.create_all(bind=engine)


# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()


# app.dependency_overrides[get_db] = override_get_db

# client = TestClient(app)


@pytest.mark.asyncio
async def test_create_user(client):
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
async def test_get_user_not_authenticated(async_client):
    response = await async_client.get("/user/deadpool")
    logger.debug("test_get_user_not_authenticated - response.text: %s" % response.text)
    assert response.status_code == 401


@pytest.mark.anyio
async def test_get_user_not_found(async_client):
    user_access_token = create_access_token(
        username="test@example.com", user_id=1, role="admin"
    )
    response = await async_client.get(
        "/user/testuser", headers={"Authorization": f"Bearer {user_access_token}"}
    )
    response = await async_client.get("/user/deadpool")
    assert response.status_code == 404, response.text


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
