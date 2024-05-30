import logging

from entertainment.models import Books
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.utils import convert_items_list_to_a_sorted_string

logger = logging.getLogger(__name__)


def book_payload(
    title: str | None = "Test Book",
    author: str | None = "John Doe",
    description: str | None = "Test description",
    genres: list[str] | None = ["Fantasy", "Fiction", "Fantasy"],
    avg_rating: float | None = 4.5,
    num_ratings: int | None = None,
    first_published: str | None = None,
) -> dict:
    payload = {
        "title": title,
        "author": author,
        "description": description,
        "genres": genres,
        "avg_rating": avg_rating,
        "num_ratings": num_ratings,
        "first_published": first_published,
    }
    return payload


def create_book(
    title: str | None = "Test Book",
    author: str | None = "John Doe",
    description: str | None = "Test description",
    genres: list[str] | None = ["Fantasy", "Fiction"],
    avg_rating: float | None = 4.5,
    num_ratings: int | None = None,
    first_published: str | None = None,
    created_by: str | None = "John_Doe",
):
    if isinstance(genres, list):
        genres = convert_items_list_to_a_sorted_string(genres)

    book = Books(
        title=title,
        author=author,
        description=description,
        genres=genres,
        avg_rating=avg_rating,
        num_ratings=num_ratings,
        first_published=first_published,
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
