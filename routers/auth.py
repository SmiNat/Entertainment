import logging
import uuid
from typing import Annotated

from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette import status

from enums import RoleEnum
from exceptions import DatabaseError
from database import SessionLocal
from models import Users

# to silence AttributeError: module 'bcrypt' has no attribute '__about__'
# which is not an error, just a warning that passlib attempts to read a version
# and fails because it's loading modules that no longer exist in bcrypt 4.1.x.
logging.getLogger('passlib').setLevel(logging.ERROR)

router = APIRouter(prefix="/auth", tags=["authorization"])

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


class CreateUser(BaseModel):

    username: str = Field(min_length=5)
    email: EmailStr
    first_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    password: str = Field(min_length=8)
    role: RoleEnum = Field(default=RoleEnum.user)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, new_user: CreateUser) -> None:
    user_model = Users(
        user_id=uuid.uuid4(),
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password),
        role=new_user.role
    )

    try:
        db.add(user_model)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
        )
