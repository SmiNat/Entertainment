import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from enums import RoleEnum
from exceptions import DatabaseError
from models import Users

load_dotenv()

# to silence AttributeError: module 'bcrypt' has no attribute '__about__'
# which is not an error, just a warning that passlib attempts to read a version
# and fails because it's loading modules that no longer exist in bcrypt 4.1.x.
logging.getLogger("passlib").setLevel(logging.ERROR)

router = APIRouter(prefix="/auth", tags=["authorization"])

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


class CreateUser(BaseModel):

    username: str = Field(min_length=5)
    email: EmailStr
    first_name: str = Field(min_length=2)
    last_name: str = Field(min_length=2)
    password: str = Field(min_length=8)
    role: RoleEnum = Field(default=RoleEnum.user)


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


def create_access_token(
    username: str, user_id: uuid, expires_delta: timedelta | None = None
):
    payload_to_encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload_to_encode.update({"exp": expire})
    return jwt.encode(payload_to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get("sub")
        user_id: uuid = payload.get("id")
        if not username or not user_id:
            return HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Could not validate credentials."
            )
        return {"username": username, "id": user_id}
    except JWTError:
        return HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Could not validate credentials."
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, new_user: CreateUser) -> None:
    user_model = Users(
        user_id=uuid.uuid4(),
        username=new_user.username,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        hashed_password=bcrypt_context.hash(new_user.password),
        role=new_user.role,
    )

    try:
        db.add(user_model)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
        )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    user = authenticate_user(form_data.username, form_data.password, db)
    token = create_access_token(
        user.username, str(user.user_id), timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": token, "token_type": "bearer"}
