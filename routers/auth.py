import logging
import uuid
import os
from dotenv import load_dotenv
from datetime import timedelta, datetime, timezone
from typing import Annotated

from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette import status
from jose import jwt

from enums import RoleEnum
from exceptions import DatabaseError
from database import SessionLocal
from models import Users

load_dotenv()

# to silence AttributeError: module 'bcrypt' has no attribute '__about__'
# which is not an error, just a warning that passlib attempts to read a version
# and fails because it's loading modules that no longer exist in bcrypt 4.1.x.
logging.getLogger('passlib').setLevel(logging.ERROR)

router = APIRouter(prefix="/auth", tags=["authorization"])

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CreateUser(BaseModel):

    username: str = Field(min_length=5)
    email: EmailStr
    first_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    password: str = Field(min_length=8)
    role: RoleEnum = Field(default=RoleEnum.user)
    is_active: bool = True


class Token(BaseModel):

    access_token: str
    token_type: str


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(username: str, password: str, db: Session):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"User '{username}' not found in the database."
        )
    if not bcrypt_context.verify(password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Failed Authentication - incorrect password."
        )
    return user


def create_access_token(username: str, user_id: uuid, expires_delta: timedelta | None = None):
    data_to_encode = {"sub": username, "id": user_id}
    expire = datetime.now(timezone.utc) + expires_delta if expires_delta else timedelta(minutes=15)
    data_to_encode.update({"exp": expire})
    return jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)


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


@router.post("/token", description="Login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,

):
    user = authenticate_user(form_data.username, form_data.password, db)
    token = create_access_token(user.username, str(user.user_id), timedelta(minutes=30))

    return {"access_token": token, "token_type": "bearer"}
