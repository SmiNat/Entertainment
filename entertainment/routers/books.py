import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import extract, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import Books
from entertainment.routers.auth import get_current_user
from entertainment.routers.utils import (
    check_if_author_or_admin,
    check_items_list,
    convert_items_list_to_a_sorted_string,
    convert_list_to_unique_values,
    get_unique_row_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def fetch_accessible_book_genres(db: Session = Depends(get_db)) -> list[str]:
    return get_unique_row_data(db, "books", "genres")


class BookRequest(BaseModel):
    title: str
    author: str
    description: str | None = Field(default=None, examples=[None])
    genres: list[str]
    avg_rating: float | None = Field(
        default=None,
        ge=0,
        le=5,
        description="Average rating from 'goodreads' score (from 0 to 5.0).",
    )
    num_ratings: int | None = Field(
        default=None, description="Number of rating scores."
    )
    first_published: datetime.date | None = Field(
        default=None, description="YYYY-MM-DD format.", examples=["2022-10-10"]
    )

    class DictConfig:
        from_attributes = True


def get_accessible_book_genres(db: Session = Depends(get_db)):
    return get_unique_row_data(db, "books", "genres")


class BookResponse(BookRequest):
    genres: str
    id: int
    created_by: str | None
    updated_by: str | None

    class DictConfig:
        from_attributes = True


class UpdateBookRequest(BookRequest):
    title: str | None = Field(default=None, examples=[None])
    author: str | None = Field(default=None, examples=[None])
    genres: list[str | None] | None = Field(
        default=[None], examples=[[None, None]], description="Provide genres as a list."
    )


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
    # response_model=None,
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


@router.get(
    "/search",
    status_code=200,
    response_model=None,
)
async def search_books(
    db: db_dependency,
    title: str = "",
    author: str = "",
    genre_primary: str = "",
    genre_secondary: str = "",
    min_rating: float | None = Query(default=0, ge=0, le=5),
    min_votes: int | None = Query(default=0, ge=0),
    published_year: int | None = Query(
        default=None, description="Year of publication of the book."
    ),
    exclude_empty_data: bool = Query(
        default=False,
        description="To exclude from search records with empty rating score or votes.",
    ),
    page: int = Query(default=1, gt=0),
):
    query = db.query(Books).filter(
        Books.title.icontains(title),
        Books.author.icontains(author),
        Books.genres.icontains(genre_primary),
        Books.genres.icontains(genre_secondary),
    )

    if exclude_empty_data is True:
        query = query.filter(
            Books.avg_rating >= min_rating,
            Books.num_ratings >= min_votes,
        )
    else:
        query = query.filter(
            or_(Books.avg_rating >= min_rating, Books.avg_rating.is_(None)),
            or_(Books.num_ratings >= min_votes, Books.num_ratings.is_(None)),
        )

    if published_year is not None:
        query = query.filter(extract("year", Books.first_published) == published_year)

    logger.debug("Database hits (search books): %s." % len(query.all()))

    results = query.offset((page - 1) * 10).limit(10).all()
    return {"number of books": len(query.all()), "books": results}


@router.post("/add", status_code=201, response_model=BookResponse)
async def add_book(
    user: user_dependency,
    db: db_dependency,
    new_book: BookRequest,
    accessible_book_genres: list[str] = Depends(fetch_accessible_book_genres),
):
    book = Books(**new_book.model_dump(), created_by=user["username"])

    # Validate genres and convert a list to a string
    check_items_list(new_book.genres, accessible_book_genres)
    genres = convert_items_list_to_a_sorted_string(new_book.genres)
    book.genres = genres

    try:
        db.add(book)
        db.commit()
        db.refresh(book)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A book with that title and that author already exists in the database."
        )

    logger.debug(
        "Book: '%s' was successfully added to database by the '%s' user."
        % (book.title, user["username"])
    )
    return book


@router.patch("/{title}/{author}", status_code=status.HTTP_202_ACCEPTED)
async def update_book(
    title: str,
    author: str,
    db: db_dependency,
    user: user_dependency,
    book_update: UpdateBookRequest,
    accessible_book_genres: list[str] = Depends(fetch_accessible_book_genres),
):
    logger.debug("Book to update: '%s' (%s)." % (title, author))

    book = (
        db.query(Books)
        .filter(
            func.lower(Books.title) == title.strip().casefold(),
            func.lower(Books.author) == author.strip().casefold(),
        )
        .first()
    )
    if not book:
        raise RecordNotFoundException(
            extra_data=f"Searched book: '{title}', (by {author})."
        )

    # Verify if user is authorized to update a book
    check_if_author_or_admin(user, book)

    fields_to_update = book_update.model_dump(exclude_none=True, exclude_unset=True)
    if "genres" in fields_to_update.keys() and all(
        genre is None for genre in fields_to_update["genres"]
    ):
        del fields_to_update["genres"]
    if not fields_to_update:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="No data input provided."
        )
    logger.debug("Fields to update: %s" % fields_to_update)

    for field, value in fields_to_update.items():
        logger.debug("Updating: field: %s, value: %s" % (field, value))
        if field == "genres":
            check_items_list(value, accessible_book_genres)
            setattr(book, field, convert_items_list_to_a_sorted_string(value))
        else:
            setattr(book, field, value)
    book.updated_by = user["username"]

    try:
        db.commit()
        db.refresh(book)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A book with that title and that author already exists in the database."
        )

    logger.debug(
        "Book '%s' (%s) was successfully updated by the '%s' user."
        % (title, author, user["username"])
    )

    return book


@router.delete("/{title}/{author}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    db: db_dependency, user: user_dependency, title: str, author: str
):
    logger.debug("Book to delete: '%s' (by %s)." % (title, author))

    book = (
        db.query(Books)
        .filter(
            func.lower(Books.title) == title.lower().casefold(),
            func.lower(Books.author) == author.lower().casefold(),
        )
        .first()
    )
    if not book:
        raise RecordNotFoundException(
            extra_data=f"Searched book: '{title}', (by {author})."
        )

    # Verify if user is authorized to update a book
    check_if_author_or_admin(user, book)

    db.delete(book)
    db.commit()

    logger.debug(
        "Book '%s' (by %s) was successfully deleted by the '%s' user."
        % (title, author, user["username"])
    )
