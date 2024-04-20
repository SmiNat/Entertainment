import datetime
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# from entertainment.database import SessionLocal
from entertainment.database import get_db
from entertainment.enums import UserRole
from entertainment.exceptions import DatabaseError
from entertainment.models import Users

from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user", tags=["user"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# async def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class User(BaseModel):
    username: str = Field(min_length=5)
    email: EmailStr
    first_name: str | None = Field(min_length=2, examples=[None])
    last_name: str | None = Field(min_length=2, examples=[None])


class CreateUser(User):
    password: str = Field(min_length=8, format="password")
    confirm_password: str = Field(min_length=8, format="password")


class GetUser(User):
    id: uuid.UUID
    role: str
    is_active: bool
    create_timestamp: datetime.datetime
    update_timestamp: datetime.datetime

    class Config:
        from_attributes = True


class UpdateUser(User):
    username: str | None = Field(min_length=5, examples=[None])
    email: EmailStr | None = Field(examples=[None])


class ChangePassword(BaseModel):
    current_password: str = Field(format="password")
    new_password: str = Field(min_length=8, format="password")
    confirm_password: str = Field(min_length=8, format="password")


@router.get("/{username}", status_code=status.HTTP_200_OK, response_model=GetUser)
async def get_user(username: str, db: db_dependency, user: user_dependency):
    requested_user = db.query(Users).filter(Users.username == username).first()
    try:
        authenticated_user = (
            db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
            # db.query(Users).filter(Users.id == str(user["id"])).first()
            # db.query(Users).filter(Users.id == user["id"]).first()  # ??????????????????
        )
    except TypeError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Cannot validate authenicated user. Check if "
            "the session has not expired and the token is still valid.",
        )

    if not authenticated_user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Failed Authentication.")

    if not requested_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user found in the database.")

    if authenticated_user.role != UserRole.admin:
        if username != user["username"]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Permission denied. Access to see other users' data is restricted. ",
            )
    logger.debug("Get user - successfully returned a user '%s'." % username)
    return requested_user


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=GetUser)
async def create_user(db: db_dependency, new_user: CreateUser) -> dict:
    if not new_user.password == new_user.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords does not match.")

    user_model = Users(
        id=uuid.uuid4(),
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password.strip()),
        role=UserRole.user,  # for security reasons, all users created via API has 'user' role
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
        "Post on create user - successfully added a user '%s'." % user_model.username
    )
    return user_model


@router.patch("/", status_code=status.HTTP_204_NO_CONTENT)
async def update_user(
    db: db_dependency, user: user_dependency, data: UpdateUser
) -> None:
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )

    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(authenticated_user, field, value)

    db.commit()

    logger.debug(
        "Patch on update user - successfully updated a user '%s'."
        % authenticated_user.username
    )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: db_dependency, user: user_dependency) -> None:
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )

    if not authenticated_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user found in the database.")

    db.query(Users).filter(Users.id == uuid.UUID(user["id"])).delete()
    db.commit()

    logger.debug(
        "Delete user - successfully deleted a user '%s'." % authenticated_user.username
    )


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    db: db_dependency, user: user_dependency, password: ChangePassword
) -> None:
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )

    if not bcrypt_context.verify(
        password.current_password.strip(), authenticated_user.hashed_password
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Failed Authentication - incorrect current password.",
        )

    if not password.new_password.strip() == password.confirm_password.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords does not match.")

    authenticated_user.hashed_password = bcrypt_context.hash(
        password.new_password.strip()
    )
    db.add(authenticated_user)
    db.commit()

    logger.debug(
        "Put on change password - successfully changed password for a user '%s'."
        % authenticated_user.username
    )
