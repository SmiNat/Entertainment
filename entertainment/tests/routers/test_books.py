import datetime
import logging
from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy import func

from entertainment.models import Books
from entertainment.routers.books import fetch_accessible_book_genres
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_books import (
    book_payload,
    check_if_db_books_table_is_not_empty,
    create_book,
)
from entertainment.tests.utils_users import create_user_and_token

logger = logging.getLogger(__name__)


def test_get_unique_row_data_with_fixture():
    with patch("entertainment.routers.books.get_unique_row_data") as mock_function:
        mock_function.return_value = ["value1", "value2", "value3"]
        result = fetch_accessible_book_genres(TestingSessionLocal())
        assert result == ["value1", "value2", "value3"]


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
    book = create_book("Test book")
    assert check_if_db_books_table_is_not_empty() is True
    expected_result = {
        "number_of_books": 1,
        "page": "1 of 1",
        "books": [jsonable_encoder(book, exclude_none=True)],
    }

    response = await async_client.get("/books/all")
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_result == response.json()


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
    expected_result = {
        "number_of_books": 5,
        "page": "3 of 3",
        "books": [
            {
                "id": 5,
                "title": "5",
                "author": "John Doe",
                "description": "Test description",
                "genres": "Fantasy, Fiction",
                "avg_rating": 4.5,
                "created_by": "John_Doe",
            }
        ],
    }
    response = await async_client.get("/books/all", params=params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 200
    assert expected_result == response.json()

    # Empty page
    params = {"page_size": 4, "page_number": 3}
    expected_result = "Books not found"
    response = await async_client.get("/books/all", params=params)
    assert response.status_code == 404
    assert expected_result in response.json()["detail"]

    # Page size out of range
    params = {"page_size": 222, "page_number": 3}
    response = await async_client.get("/books/all", params=params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 422
    assert "Input should be less than or equal to 100" in response.text


@pytest.mark.anyio
async def test_search_books_200_empty_db(async_client: AsyncClient):
    expected_response = "Books not found."
    response = await async_client.get("/books/search")
    assert response.status_code == 404
    assert expected_response == response.json()["detail"]


@pytest.mark.anyio
async def test_search_books_200_with_non_empty_db_and_exclude_empty_data_param(
    async_client: AsyncClient,
):
    create_book(
        "Test book", first_published=datetime.date(2011, 11, 11), num_ratings=None
    )
    assert check_if_db_books_table_is_not_empty() is True

    # Case with exclude_empty_data query parameter set to False
    expected_response = "Books not found."
    response = await async_client.get(
        "/books/search", params={"exclude_empty_data": True}
    )
    logger.debug("Response: %s" % response.json())
    assert response.status_code == 404
    assert expected_response == response.json()["detail"]


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
        "number_of_books": 1,
        "page": "1 of 1",
        "books": [
            {
                "id": 1,
                "title": "Test book",
                "author": "John Doe",
                "description": "Test description",
                "genres": "Fantasy, Fiction",
                "avg_rating": 4.5,
                "first_published": "2011-11-11",
                "created_by": "John_Doe",
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
    "search_params, no_of_books, books, status_code",
    [
        ({"title": "book"}, 2, [1, 2], 200),
        ({"genre_primary": "Novels"}, 2, [1, 3], 200),
        ({"genre_primary": "Novels", "genre_secondary": "action"}, 1, [1], 200),
        ({"genre_primary": "Novels", "min_rating": 4.0}, 1, [3], 200),
        (
            {"genre_primary": "Novels", "min_rating": 4.0, "exclude_empty_data": True},
            0,
            [],
            404,
        ),
        ({"author": "Doe", "published_year": 1995}, 1, [3], 200),
        ({"min_rating": 2, "min_votes": 100}, 3, [1, 2, 3], 200),
        ({"min_rating": 2, "min_votes": 100, "exclude_empty_data": True}, 1, [1], 200),
    ],
)
@pytest.mark.anyio
async def test_search_books_200_different_scenarios(
    async_client: AsyncClient,
    search_params: dict,
    no_of_books: int,
    books: list,
    status_code: int,
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
        "number_of_books": no_of_books,
        "page": "1 of 1",
        "books": [jsonable_encoder(options[book], exclude_none=True) for book in books],
    }
    response = await async_client.get("/books/search", params=search_params)
    logger.debug("Response: %s" % response.json())
    assert response.status_code == status_code
    if status_code == 200:
        assert expected_response == response.json()
    elif status_code == 404:
        assert "Books not found" in response.json()["detail"]


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
    with patch("entertainment.routers.books.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Classics", "Fantasy", "Fiction", "Romance"]
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
async def test_add_book_422_not_unique_book(
    async_client: AsyncClient,
    created_token: str,
    invalid_title: dict,
    comment: str,
    added_book: Books,
):
    """The user can only create a book with unique title and author."""
    payload = {
        "title": invalid_title,
        "author": added_book.author,
        "genres": ["fantasy"],
    }

    with patch("entertainment.routers.books.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Classics", "Fantasy", "Fiction", "Romance"]
        response = await async_client.post(
            "/books/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert (
            "Unique constraint failed. A book with that title and that author already exists in the database."
            in response.json()["detail"]
        )


@pytest.mark.parametrize(
    "payload, exp_response, status_code, comment",
    [
        (
            {"title": "test", "author": "test", "genres": ["fiction", "romance"]},
            '{"title":"test","author":"test","description":null,"genres":"Fiction, Romance",',
            201,
            "all valid - check output",
        ),
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
            {"title": "test", "author": "JD", "genres": ["fiction", "invalid"]},
            "Invalid genre: check 'get genres' for list of accessible genres",
            422,
            "invalid genre - genre not allowed",
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
                "genres": ["fiction", "comedy"],
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
):
    with patch("entertainment.routers.books.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Classics", "Fantasy", "Fiction", "Romance"]
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
    added_book: Books,
    path_param: str,
    value: str,
    comment: str,
):
    user, token = created_user_token

    title = value if path_param == "title" else added_book.title
    author = value if path_param == "author" else added_book.author

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

    with patch("entertainment.routers.books.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Classics", "Fantasy", "Fiction", "Romance"]
        response = await async_client.patch(
            f"/books/{title}/{author}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 202
        assert expected_result == response.json()


@pytest.mark.anyio
async def test_update_book_401_if_not_authenticated(
    async_client: AsyncClient, added_book: Books
):
    payload = book_payload()
    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author), json=payload
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.text


@pytest.mark.anyio
async def test_update_book_404_if_book_not_found(
    async_client: AsyncClient, added_book: Books, created_token: str
):
    invalid_title = {"title": "invalid", "author": added_book.author}
    invalid_author = {"title": added_book.title, "author": "invalid"}
    invalid_data = [invalid_title, invalid_author]

    for element in invalid_data:
        response = await async_client.patch(
            "/books/{0}/{1}".format(element["title"], element["author"]),
            json={"avg_rating": 1.1},
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 404
        assert (
            "The record was not found in the database. Searched book: '{0}', (by {1}).".format(
                element["title"], element["author"]
            )
            in response.json()["detail"]
        )


@pytest.mark.anyio
async def test_update_book_202_update_by_the_record_creator(
    async_client: AsyncClient, added_book: Books, created_user_token: str
):
    user, token = created_user_token
    assert added_book.created_by == user["username"]
    assert added_book.avg_rating != 1.1
    assert added_book.updated_by != user["username"]

    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json={"avg_rating": 1.1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert response.json()["avg_rating"] == 1.1
    assert response.json()["updated_by"] == user["username"]


@pytest.mark.anyio
async def test_update_book_202_update_by_the_admin(
    async_client: AsyncClient, added_book: Books, created_user_token: str
):
    admin_user, token = create_user_and_token(
        "admin_user", "admin@example.com", "password", "admin"
    )
    assert added_book.created_by != "admin_user"
    assert added_book.avg_rating != 1.1
    assert added_book.updated_by != "admin_user"

    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json={"avg_rating": 1.1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert response.json()["avg_rating"] == 1.1
    assert response.json()["updated_by"] == "admin_user"


@pytest.mark.anyio
async def test_update_book_403_update_by_the_user_who_is_not_the_book_creator(
    async_client: AsyncClient, added_book: Books, created_user_token: str
):
    some_user, token = create_user_and_token(
        "some_user", "user@example.com", "password", "user"
    )
    assert added_book.created_by != "some_user"
    assert added_book.avg_rating != 1.1

    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json={"avg_rating": 1.1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the "
        "database record can change or delete the record from the database"
        in response.text
    )


@pytest.mark.parametrize(
    "new_title, new_author, comment",
    [
        ("Test book", "JD", "the same title and author as of already existing book"),
        ("test book", "jd", "lowercase title and author as of already existing book"),
        (
            "    Test book  ",
            "  JD   ",
            "whitespaced title and author as of already existing book",
        ),
    ],
)
@pytest.mark.anyio
async def test_update_book_422_not_unique_book(
    async_client: AsyncClient,
    created_token: str,
    added_book: Books,
    new_title: str,
    new_author: str,
    comment: str,
):
    some_existing_book = create_book(title="Test book", author="JD")
    assert some_existing_book.title != added_book.title
    assert some_existing_book.title != added_book.author

    payload = {"title": new_title, "author": new_author}

    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert (
        "Unique constraint failed. A book with that title and that author already exists in the database."
        in response.text
    )


@pytest.mark.parametrize(
    "invalid_payload, comment",
    [
        ({"genres": [None, None]}, "empty genres list"),
        ({}, "nothing to change"),
    ],
)
@pytest.mark.anyio
async def test_update_book_400_if_no_data_to_change(
    async_client: AsyncClient,
    created_token: str,
    added_book: Books,
    invalid_payload: dict,
    comment: str,
):
    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json=invalid_payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 400
    assert "No data input provided" in response.json()["detail"]


@pytest.mark.parametrize(
    "invalid_payload, status_code, error_msg",
    [
        (
            {"genres": ["invalid"]},
            422,
            "Invalid genre: check 'get genres' for list of accessible genres",
        ),
        ({"avg_rating": 6.7}, 422, "Input should be less than or equal to 5"),
        ({"num_ratings": "ten"}, 422, "Input should be a valid integer"),
        (
            {"first_published": "22 October 2020"},
            422,
            "Input should be a valid date or datetime",
        ),
    ],
)
@pytest.mark.anyio
async def test_update_book_422_incorrect_update_data(
    async_client: AsyncClient,
    added_book: Books,
    created_token: str,
    invalid_payload: dict,
    status_code: int,
    error_msg: str,
):
    response = await async_client.patch(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        json=invalid_payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == status_code
    assert error_msg in response.text


@pytest.mark.anyio
async def test_delete_book_204(
    async_client: AsyncClient, created_token: str, added_book: Books
):
    # Checking if the book exists in db
    book = (
        TestingSessionLocal()
        .query(Books)
        .filter(
            func.lower(Books.author) == added_book.author.lower().casefold(),
            func.lower(Books.title) == added_book.title.lower().casefold(),
        )
        .first()
    )
    assert book is not None
    logger.debug(
        "Book to delete: '%s' (by %s)." % (added_book.title, added_book.author)
    )

    # Calling the endpoint
    response = await async_client.delete(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 204

    # Checking if the book no longer exists in db
    book = (
        TestingSessionLocal()
        .query(Books)
        .filter(Books.title == added_book.title)
        .first()
    )
    assert book is None


@pytest.mark.anyio
async def test_delete_book_401_not_authenticated(
    async_client: AsyncClient, added_book: Books
):
    response = await async_client.delete(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_book_404_book_not_found(
    async_client: AsyncClient, created_token: str
):
    response = await async_client.delete(
        "/books/fake title/fake author",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "The record was not found in the database" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_book_204__by_the_admin_user(
    async_client: AsyncClient, created_user_token: tuple, added_book: Books
):
    # Checking if the book exists in db
    book = (
        TestingSessionLocal()
        .query(Books)
        .filter(
            func.lower(Books.author) == added_book.author.lower().casefold(),
            func.lower(Books.title) == added_book.title.lower().casefold(),
        )
        .first()
    )
    assert book is not None
    logger.debug(
        "Book to delete: '%s' (by %s)." % (added_book.title, added_book.author)
    )

    # Creating a user who is not the book creator but is an admin user
    admin_user, token = create_user_and_token(username="admin_user", role="admin")
    assert admin_user.username != book.created_by

    # Calling the endpoint
    response = await async_client.delete(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Checking if the book no longer exists in db
    book = (
        TestingSessionLocal()
        .query(Books)
        .filter(Books.title == added_book.title)
        .first()
    )
    assert book is None


@pytest.mark.anyio
async def test_delete_book_403_forbidden_if_not_admin_or_book_creator(
    async_client: AsyncClient, added_book: Books
):
    some_user, token = create_user_and_token(username="some_user", role="user")
    assert added_book.created_by != some_user.username

    response = await async_client.delete(
        "/books/{0}/{1}".format(added_book.title, added_book.author),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the database record "
        "can change or delete the record from the database."
        in response.json()["detail"]
    )
