import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.models import Books
from entertainment.routers.auth import get_current_user
from entertainment.routers.utils import convert_list_to_unique_values

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class BookRequest(BaseModel):
    title: str
    author: str
    description: str | None = Field(default=None, examples=[None])
    genres: list[str]
    avg_rating: float | None = Field(
        default=2.2,
        ge=0,
        le=5,
        description="Average rating from 'goodreads' score.",
    )
    num_ratings: int | None = Field(
        default=None, description="Number of rating scores."
    )
    first_published: datetime.date | None = Field(
        default=None, description="YYYY-MM-DD format.", examples=["2022-22-10"]
    )

    class DictConfig:
        from_attributes = True


class BookResponse(BookRequest):
    genres: str
    id: int
    created_by: str | None
    updated_by: str | None

    class DictConfig:
        from_attributes = True


@router.get("/genres", status_code=200, description="Get all available book genres.")
async def get_books_genres(db: db_dependency) -> list:
    query = select(Books.genres).distinct()
    genres = db.execute(query).scalars().all()
    unique_genres = convert_list_to_unique_values(genres)
    logger.debug("Number of available book genres: %s." % len(unique_genres))
    return unique_genres


@router.get(
    "/all",
    status_code=200,
    response_model=list[BookResponse],
    response_model_exclude_none=True,
)
async def get_all_books(
    db: db_dependency,
    page_size: int = Query(
        default=10, gt=0, le=100, description="Number of records per page."
    ),
    page_number: int = Query(1, gt=0),
) -> list[Books]:
    books = db.query(Books).all()
    if not books:
        raise HTTPException(404, "Books not found.")

    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    logger.debug("Database hits (all books): %s records." % len(books))

    return books[start_index:end_index]
