import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from entertainment.database import get_db
from entertainment.enums import TokenExp
from entertainment.exceptions import CredentialsException
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

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


db_dependency = Annotated[Session, Depends(get_db)]


def access_token_expire_minutes() -> int:
    return TokenExp.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(
    username: str,
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
):
    payload_to_encode = {"sub": username, "id": user_id, "role": role}
    logger.debug("Payload for create_access_token: %s" % payload_to_encode)

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=access_token_expire_minutes()
        )
    payload_to_encode.update({"exp": expire})

    logger.debug("Access token created for the user: %s." % username)

    return jwt.encode(payload_to_encode, SECRET_KEY, algorithm=ALGORITHM)


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


async def get_current_user(
    db: db_dependency, token: Annotated[str, Depends(oauth2_bearer)]
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        logger.debug("Payload for get_current_user: %s" % payload)
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        logger.debug(
            "Current user data: username: %s, id: %s, role: %s."
            % (username, user_id, user_role)
        )

        if username is None or user_id is None or user_role is None:
            raise CredentialsException()

        # Validate, if user is still in DB (user can delete an account after which
        # all authorized accesses should be forbidden)
        user = db.query(Users).filter_by(id=user_id, username=username).first()
        if not user or user.is_active is False:
            logger.debug(
                "No user '%s' (id: %s) in DB or user has inactive status."
                % (username, user_id)
            )
            raise CredentialsException()

        return {"username": username, "id": user_id, "role": user_role}

    except ExpiredSignatureError as e:
        raise CredentialsException(detail="Token has expired.") from e

    except JWTError:
        raise CredentialsException()


@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
) -> dict[str, str]:
    user = authenticate_user(form_data.username.strip(), form_data.password.strip(), db)
    token = create_access_token(
        user.username,
        str(user.id),
        user.role,
        timedelta(minutes=TokenExp.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    logger.debug("Access token returned for the user: %s." % user.username)

    return {"access_token": token, "token_type": "bearer"}
