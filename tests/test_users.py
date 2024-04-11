import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from database import Base, create_db, create_sqlite_engine
from main import app
from routers.users import get_db

test_db = "./tests/test.db"

create_db(test_db)

# SQLALCHEMY_TEST_DATABASE_URL = "sqlite://"
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./tests/test.db"

engine = create_sqlite_engine(SQLALCHEMY_TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_user():
    request_data = {
        "username": "deadpool",
        "email": "deadpool@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "deadpool123",
        "confirm_password": "deadpool123",
    }
    response = client.post("/user", json=request_data)

    assert response.status_code == 201, response.text
    data = response.json()
    # assert data["email"] == "deadpool@example.com"
    # assert "user_id" in data
    # user_id = data["user_id"]
    # username = data["username"]


@pytest.mark.asyncio
async def test_get_user():
    response = client.get("/user/deadpool")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "deadpool@example.com"
    assert data["role"] == "user"
