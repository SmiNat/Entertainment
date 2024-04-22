import logging
import os

# import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

# from entertainment.database import SessionLocal
from entertainment.database import get_db
from entertainment.models import Users

load_dotenv()

# To silence AttributeError: module 'bcrypt' has no attribute '__about__'
# which is not an error, just a warning that passlib attempts to read a version
# and fails because it's loading modules that no longer exist in bcrypt 4.1.x.
logging.getLogger("passlib").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authorization"])

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


# async def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


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
    logger.debug("Authenticated user: '%s'." % user.username)
    return user


def create_access_token(
    # username: str, user_id: uuid, role: str, expires_delta: timedelta | None = None
    username: str,
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
):
    payload_to_encode = {"sub": username, "id": user_id, "role": role}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    payload_to_encode.update({"exp": expire})

    logger.debug("Access token created for the user '%s'." % username)

    return jwt.encode(payload_to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get("sub")
        # user_id: uuid = payload.get("id")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        if not username or not user_id:
            return HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Could not validate credentials."
            )
        logger.debug("Current user: '%s'." % username)
        return {"username": username, "id": user_id, "role": user_role}
    except JWTError:
        return HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Could not validate credentials."
        )


@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
) -> dict[str, str]:
    user = authenticate_user(form_data.username, form_data.password, db)
    token = create_access_token(
        user.username,
        str(user.id),
        user.role,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.debug("Access token returned for the user '%s'." % user.username)

    return {"access_token": token, "token_type": "bearer"}
