import logging

from entertainment.models import Books
from entertainment.tests.conftest import TestingSessionLocal

logger = logging.getLogger(__name__)


def book_payload(
    title: str | None = "Test Book",
    author: str | None = "John Doe",
    description: str | None = "Test description",
    genres: list[str] | None = ["Fantasy", "Fiction"],
    avg_rating: float | None = 4.5,
    rating_reviews: int | None = None,
) -> dict:
    payload = {
        "title": title,
        "author": author,
        "description": description,
        "genres": genres,
        "avg_rating": avg_rating,
        "rating_reviews": rating_reviews,
    }
    return payload


def create_book(
    title: str | None = "Test Book",
    author: str | None = "John Doe",
    description: str | None = "Test description",
    genres: list[str] | None = ["Fantasy", "Fiction"],
    avg_rating: float | None = 4.5,
    rating_reviews: int | None = None,
    created_by: str | None = "John_Doe",
):
    if isinstance(genres, list):
        genres = ", ".join(genres)

    book = Books(
        title=title,
        author=author,
        description=description,
        genres=genres,
        avg_rating=avg_rating,
        rating_reviews=rating_reviews,
        created_by=created_by,
    )

    db = TestingSessionLocal()
    try:
        db.add(book)
        db.commit()
        db.refresh(book)
        return book
    finally:
        # db.execute(text("DELETE FROM books"))
        # db.commit()
        db.close()


def check_if_db_books_table_is_not_empty() -> bool:
    db = TestingSessionLocal()
    db_content = db.query(Books).all()
    if db_content:
        return True
    return False
