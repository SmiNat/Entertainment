import datetime
import logging

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Books
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_books import (
    book_payload,
    check_if_db_books_table_is_not_empty,
    create_book,
)

logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_get_books_genres_empty_db(async_client: AsyncClient):
    response = await async_client.get("/books/genres")
    assert response.status_code == 200
    assert [] == response.json()


@pytest.mark.anyio
async def test_get_books_genres_non_empty_db(async_client: AsyncClient):
    book1 = create_book("Book 1", genres=["Romance", "Fantasy"])
    book2 = create_book("Book 2", genres=["Romance", "Fiction", "classics"])
    book3 = create_book("Book 3", genres=["Epic fantasy", "Horror"])
    logger.debug(
        "Database records: %s, %s, %s"
        % (jsonable_encoder(book1), jsonable_encoder(book2), jsonable_encoder(book3))
    )
    expected_response = [
        "Classics",
        "Epic Fantasy",
        "Fantasy",
        "Fiction",
        "Horror",
        "Romance",
    ]

    response = await async_client.get("/books/genres")
    assert response.status_code == 200
    assert response.json() == expected_response


@pytest.mark.anyio
async def test_get_all_books_200_non_empty_db(async_client: AsyncClient):
    create_book("Test book")
    assert check_if_db_books_table_is_not_empty() is True

    response = await async_client.get("/books/all")
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert "Test book" in response.json()[0]["title"]
    assert len(response.json()) == 1


@pytest.mark.anyio
async def test_get_all_books_404_empty_db(async_client: AsyncClient):
    assert check_if_db_books_table_is_not_empty() is False

    response = await async_client.get("/books/all")
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 404
    assert "Books not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_all_books_pagination(async_client: AsyncClient):
    # Creating multiple books
    for book in range(1, 6):
        create_book(title=str(book))
    assert len(TestingSessionLocal().query(Books).all()) == 5

    # Last non empty page with 1 record
    params = {"page_size": 2, "page_number": 3}
    expected_result = [
        {
            "id": 5,
            "title": "5",
            "author": "John Doe",
            "description": "Test description",
            "genres": "Fantasy, Fiction",
            "avg_rating": 4.5,
            "created_by": "John_Doe",
        }
    ]
    response = await async_client.get("/books/all", params=params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_result == response.json()

    # Empty page
    params = {"page_size": 4, "page_number": 3}
    expected_result = []
    response = await async_client.get("/books/all", params=params)
    assert response.status_code == 200
    assert expected_result == response.json()

    # Page size out of range
    params = {"page_size": 222, "page_number": 3}
    response = await async_client.get("/books/all", params=params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 422
    assert "Input should be less than or equal to 100" in response.text


@pytest.mark.anyio
async def test_search_books_200_empty_db(async_client: AsyncClient):
    expected_response = {"number of books": 0, "books": []}
    response = await async_client.get("/books/search")
    assert response.status_code == 200
    assert expected_response == response.json()


@pytest.mark.anyio
async def test_search_books_200_with_non_empty_db_and_exclude_empty_data_param(
    async_client: AsyncClient,
):
    create_book(
        "Test book", first_published=datetime.date(2011, 11, 11), num_ratings=None
    )
    assert check_if_db_books_table_is_not_empty() is True

    # Case with exclude_empty_data query parameter set to False
    expected_response = {"number of books": 0, "books": []}
    response = await async_client.get(
        "/books/search", params={"exclude_empty_data": True}
    )
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_response == response.json()


@pytest.mark.anyio
async def test_search_books_200_with_non_empty_db_and_no_exclude_empty_data_param(
    async_client: AsyncClient,
):
    create_book(
        "Test book", first_published=datetime.date(2011, 11, 11), num_ratings=None
    )
    assert check_if_db_books_table_is_not_empty() is True

    # Case with exclude_empty_data query parameter set to True
    expected_response = {
        "number of books": 1,
        "books": [
            {
                "id": 1,
                "title": "Test book",
                "author": "John Doe",
                "description": "Test description",
                "genres": "Fantasy, Fiction",
                "avg_rating": 4.5,
                "num_ratings": None,
                "first_published": "2011-11-11",
                "created_by": "John_Doe",
                "updated_by": None,
            }
        ],
    }
    response = await async_client.get(
        "/books/search", params={"exclude_empty_data": False}
    )
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_response == response.json()


@pytest.mark.parametrize(
    "search_params, no_of_books, books",
    [
        ({"title": "book"}, 2, [1, 2]),
        ({"genre_primary": "Novels"}, 2, [1, 3]),
        ({"genre_primary": "Novels", "genre_secondary": "action"}, 1, [1]),
        ({"genre_primary": "Novels", "min_rating": 4.0}, 1, [3]),
        (
            {"genre_primary": "Novels", "min_rating": 4.0, "exclude_empty_data": True},
            0,
            [],
        ),
        ({"author": "Doe", "published_year": 1995}, 1, [3]),
        ({"min_rating": 2, "min_votes": 100}, 3, [1, 2, 3]),
        ({"min_rating": 2, "min_votes": 100, "exclude_empty_data": True}, 1, [1]),
    ],
)
@pytest.mark.anyio
async def test_search_books_200_different_scenarios(
    async_client: AsyncClient, search_params: dict, no_of_books: int, books: list
):
    book1 = create_book(
        title="A book",
        author="JD",
        genres=["Action", "Fiction", "Novels"],
        avg_rating=2.2,
        num_ratings=999,
        first_published=datetime.date(2010, 10, 10),
    )
    book2 = create_book(
        title="New book",
        author="John Doe",
        genres=["Romance", "Poetry"],
        avg_rating=3.5,
        num_ratings=None,
    )
    book3 = create_book(
        title="New test",
        author="Doe",
        genres=["Fantasy", "Fiction", "Novels"],
        avg_rating=None,
        num_ratings=222,
        first_published=datetime.date(1995, 11, 22),
    )
    options = {1: book1, 2: book2, 3: book3}
    expected_response = {
        "number of books": no_of_books,
        "books": [jsonable_encoder(options[book]) for book in books],
    }
    response = await async_client.get("/books/search", params=search_params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_response == response.json()


@pytest.mark.anyio
async def test_add_book_201(async_client: AsyncClient, created_token: str):
    payload = {"title": "Test book", "author": "JD", "genres": ["fiction"]}
    expected_response = {
        "title": "Test book",
        "author": "JD",
        "genres": "Fiction",
        "description": None,
        "id": 1,
        "avg_rating": None,
        "num_ratings": None,
        "first_published": None,
        "created_by": "testuser",
        "updated_by": None,
    }
    response = await async_client.post(
        "/books/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 201
    assert expected_response == response.json()


@pytest.mark.anyio
async def test_add_book_401_if_not_authenticated(async_client: AsyncClient):
    payload = {"title": "test book", "author": "JD", "genres": ["fiction"]}
    response = await async_client.post("/books/add", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_title, comment",
    [
        ("new book", "the same book title"),
        ("New BOOK", "the same book title - case insensitive"),
        (" New Book   ", "the same book title - stripped from whitespaces"),
    ],
)
async def test_add_movie_422_not_unique_book(
    async_client: AsyncClient,
    created_token: str,
    invalid_title: dict,
    comment: str,
    added_book: dict,
):
    """The user can only create a book with unique title and author."""
    payload = {
        "title": invalid_title,
        "author": added_book["author"],
        "genres": ["fantasy"],
    }

    response = await async_client.post(
        "/books/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert (
        "Unique constraint failed: Record already exists in the database."
        in response.json()["detail"]
    )


@pytest.mark.parametrize(
    "payload, exp_response, status_code, comment",
    [
        (
            {"title": "test", "author": None, "genres": ["fiction"]},
            "Input should be a valid string",
            422,
            "missing required field",
        ),
        (
            {"title": "test", "author": "JD", "genres": "fiction"},
            "Input should be a valid list",
            422,
            "invalid genre data type",
        ),
        (
            {"title": "test", "author": "JD", "genres": ["fiction"], "avg_rating": 7},
            "Input should be less than or equal to 5",
            422,
            "rating out of range",
        ),
        (
            {
                "title": "test",
                "author": "JD",
                "genres": ["fiction"],
                "num_ratings": 10.5,
            },
            "Input should be a valid integer",
            422,
            "invalid rating data type",
        ),
        (
            {
                "title": "test",
                "author": "JD",
                "genres": ["fiction"],
                "first_published": "2022-22-22",
            },
            "Input should be a valid date or datetime",
            422,
            "invalid date",
        ),
    ],
)
@pytest.mark.anyio
async def test_add_book_422_invalid_input_data(
    async_client: AsyncClient,
    created_token: str,
    payload: dict,
    exp_response: str,
    status_code: int,
    comment: str,
    added_book: dict,
):
    response = await async_client.post(
        "/books/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == status_code
    assert exp_response in response.text


@pytest.mark.parametrize(
    "path_param, value, comment",
    [
        ("title", "New book", "valid title, the same as in db"),
        ("title", "new book", "valid title, lowercase"),
        ("title", "   New BOOK  ", "valid title, with whitespaces"),
        ("author", "John Doe", "valid author, the same as in db"),
        ("author", "john doe", "valid author, lowercase"),
        ("author", "   john DOE  ", "valid author, with whitespaces"),
    ],
)
@pytest.mark.anyio
async def test_update_book_202(
    async_client: AsyncClient,
    created_user_token: tuple,
    added_book: dict,
    path_param: str,
    value: str,
    comment: str,
):
    user, token = created_user_token

    title = value if path_param == "title" else added_book["title"]
    author = value if path_param == "author" else added_book["author"]

    payload = book_payload()
    expected_result = {
        "title": "Test Book",
        "author": "John Doe",
        "description": "Test description",
        "genres": "Fantasy, Fiction",
        "avg_rating": 4.5,
        "num_ratings": 1000,
        "first_published": "2011-11-11",
        "created_by": user["username"],
        "updated_by": user["username"],
        "id": 1,
    }

    response = await async_client.patch(
        f"/books/{title}/{author}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_update_book_401_if_not_authenticated():
    assert False
