from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/user", tags=["user"])


# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# @router.get("/token")
# async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
#     return {"token": token}


# class User(BaseModel):

#     username: str = Field(min_length=5)
#     email: EmailStr
#     first_name: str = Field(min_length=2)
#     last_name: str = Field(min_length=2)
#     password: str = Field(min_length=8)
