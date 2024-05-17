import pytest
from httpx import AsyncClient

from entertainment.tests.utils_books import create_book


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
