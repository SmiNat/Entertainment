import pytest
from httpx import AsyncClient

from entertainment.models import Books
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_books import (
    check_if_db_books_table_is_not_empty,
    create_book,
)


@pytest.mark.anyio
async def test_get_books_genres_empty_db(async_client: AsyncClient):
    response = await async_client.get("/books/genres")
    assert response.status_code == 200
    assert [] == response.json()


@pytest.mark.anyio
async def test_get_books_genres_non_empty_db(async_client: AsyncClient):
    create_book("Book 1", genres=["Romance", "Fantasy"])
    create_book("Book 2", genres=["Romance", "Fiction", "classics"])
    create_book("Book 3", genres=["Epic fantasy", "Horror"])
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
    assert response.status_code == 200
    assert "Test book" in response.json()[0]["title"]
    assert len(response.json()) == 1


@pytest.mark.anyio
async def test_get_all_books_404_empty_db(async_client: AsyncClient):
    assert check_if_db_books_table_is_not_empty() is False

    response = await async_client.get("/books/all")
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
    assert response.status_code == 422
    assert "Input should be less than or equal to 100" in response.text
