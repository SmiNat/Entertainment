import logging

from entertainment.exceptions import DatabaseNotEmptyError
from entertainment.main import app
from entertainment.models import Users
from entertainment.routers.auth import (
    create_access_token,
    get_current_user,
)
from entertainment.tests.conftest import TestingSessionLocal

logger = logging.getLogger(__name__)


# Some helpful functions to use in tests
def create_db_user(
    username: str = "testuser",
    email: str = "test@example.com",
    hashed_password: str = "password",
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


def create_user_and_token(
    username: str,
    email: str = "some@example.com",
    password: str = "password",
    role: str = "user",
):
    user = create_db_user(username, email, password, role)
    token = create_access_token(user.username, user.id, user.role)
    return user, token


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
