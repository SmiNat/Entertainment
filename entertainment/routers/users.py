import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import UserRole
from entertainment.exceptions import DatabaseError
from entertainment.models import Users

from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class User(BaseModel):
    username: str = Field(min_length=5, examples=["username"])
    email: EmailStr
    first_name: str | None = Field(default=None, min_length=2, examples=[None])
    last_name: str | None = Field(default=None, min_length=2, examples=[None])


class CreateUser(User):
    password: str = Field(min_length=8, examples=["password"])
    confirm_password: str = Field(min_length=8, examples=["password"])


class GetUser(User):
    id: int
    role: str
    is_active: bool
    create_timestamp: datetime.datetime
    update_timestamp: datetime.datetime

    class ConfigDict:
        from_attributes = True


class UpdateUser(BaseModel):
    email: EmailStr | None = Field(examples=[None])
    first_name: str | None = Field(default=None, min_length=2, examples=[None])
    last_name: str | None = Field(default=None, min_length=2, examples=[None])


class ChangePassword(BaseModel):
    current_password: str = Field(examples=["old_password"])
    new_password: str = Field(min_length=8, examples=["password"])
    confirm_password: str = Field(min_length=8, examples=["password"])


@router.get("/current")
async def get_logged_in_user(current_user: user_dependency):
    return current_user


@router.get("/check/{username}", status_code=status.HTTP_200_OK, response_model=GetUser)
async def get_user(username: str, db: db_dependency, user: user_dependency):
    requested_user = db.query(Users).filter(Users.username == username).first()

    logger.debug("Requested user at get_user endpoint: %s" % username)
    logger.debug("Authenticated user at get_user endpoint: %s" % user["username"])

    if not requested_user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "User '%s' not found in the database." % username
        )

    if user["role"] != UserRole.ADMIN:
        if username != user["username"]:
            logger.debug(
                "Searched username '%s' does not match with authenticated user '%s'."
                % (username, user["username"])
            )

            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Permission denied. Access to see other users' data is restricted.",
            )
    logger.debug("GET user - successfully returned a user '%s'." % username)
    return requested_user


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=GetUser)
async def create_user(db: db_dependency, new_user: CreateUser) -> dict:
    if db.query(Users).filter(Users.email == new_user.email).first():
        raise HTTPException(400, "A user with that email already exists.")
    if db.query(Users).filter(Users.username == new_user.username).first():
        raise HTTPException(400, "A user with that username already exists.")

    if not new_user.password == new_user.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords does not match.")

    user_model = Users(
        username=new_user.username.strip(),
        email=new_user.email.strip(),
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password.strip()),
        role=UserRole.USER,  # for security reasons, all users created via API has 'user' role
    )

    try:
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
        )

    logger.debug(
        "POST on create user - successfully added a user '%s'." % user_model.username
    )
    return user_model


@router.patch("/update", status_code=status.HTTP_204_NO_CONTENT)
async def update_user(
    db: db_dependency, user: user_dependency, data: UpdateUser
) -> None:
    authenticated_user = db.query(Users).filter(Users.id == user["id"]).first()

    updated_fields = data.model_dump(exclude_unset=True, exclude_none=True)
    try:
        for field, value in updated_fields.items():
            setattr(authenticated_user, field, value)
        db.commit()
        db.refresh(authenticated_user)
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
        )

    logger.debug(
        "PATCH on update user - successfully updated a user '%s'."
        % authenticated_user.username
    )


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: db_dependency, user: user_dependency) -> None:
    authenticated_user = db.query(Users).filter(Users.id == user["id"]).first()

    if not authenticated_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user found in the database.")

    db.query(Users).filter(Users.id == user["id"]).delete()
    db.commit()

    logger.debug("User successfully deleted.")


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    db: db_dependency, user: user_dependency, password: ChangePassword
) -> None:
    authenticated_user = db.query(Users).filter(Users.id == user["id"]).first()

    if not bcrypt_context.verify(
        password.current_password.strip(), authenticated_user.hashed_password
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Failed Authentication - incorrect current password.",
        )

    if not password.new_password.strip() == password.confirm_password.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords do not match.")

    authenticated_user.hashed_password = bcrypt_context.hash(
        password.new_password.strip()
    )
    db.add(authenticated_user)
    db.commit()
    db.refresh(authenticated_user)

    logger.debug(
        "PUT on change password - successfully changed password for a user '%s'."
        % authenticated_user.username
    )
