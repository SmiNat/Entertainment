import datetime
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import SessionLocal
from entertainment.exceptions import DatabaseError
from entertainment.models import Users

from .auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user", tags=["user"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )
    requested_user = db.query(Users).filter(Users.username == username).first()

    if not authenticated_user or not requested_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user found in the database.")

    if authenticated_user.role != "admin":
        if username != user["username"]:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Access to see other users' data is restricted. "
                "The user can only see personal information.",
            )
    return requested_user


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, new_user: CreateUser) -> None:
    if not new_user.password == new_user.confirm_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passwords does not match.")

    user_model = Users(
        id=uuid.uuid4(),
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password.strip()),
        role="user",  # for security reasons, all users created
        # via API has 'user' role
    )

    try:
        db.add(user_model)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
        )


@router.patch("/", status_code=status.HTTP_204_NO_CONTENT)
async def update_user(db: db_dependency, user: user_dependency, data: UpdateUser):
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )

    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(authenticated_user, field, value)

    db.commit()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(db: db_dependency, user: user_dependency):
    authenticated_user = (
        db.query(Users).filter(Users.id == uuid.UUID(user["id"])).first()
    )

    if not authenticated_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user found in the database.")

    db.query(Users).filter(Users.id == uuid.UUID(user["id"])).delete()
    db.commit()


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    db: db_dependency, user: user_dependency, password: ChangePassword
):
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
