import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.models import Books
from entertainment.routers.auth import get_current_user
from entertainment.routers.utils import convert_list_to_unique_values

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


db_dependencies = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.get("/genres", status_code=200, description="Get all available book genres.")
async def get_books_genres(db: db_dependencies) -> list:
    query = select(Books.genres).distinct()
    genres = db.execute(query).scalars().all()
    unique_genres = convert_list_to_unique_values(genres)
    logger.debug("Number of available book genres: %s." % len(unique_genres))
    return unique_genres
