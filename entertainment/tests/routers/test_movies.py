import os
from unittest.mock import patch  # noqa

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from entertainment.models import Movies, Users  # noqa
from entertainment.routers.movies import check_date, check_genre
from entertainment.tests.conftest import (  # noqa
    TestingSessionLocal,
    override_get_db,
)
from entertainment.tests.utils_movies import *  # noqa

os.environ["ENV_STATE"] = "test"

import logging  # noqa

logger = logging.getLogger(__name__)


@pytest.mark.anyio
async def test_check_date():
    invalid_date = "20-10-2020"
    # Example test case where date is invalid
    check_date("2020-10-20")

    # Example test case where date is invalid
    with pytest.raises(HTTPException) as exc_info:
        check_date(invalid_date)
    assert (
        "Invalid date type. Enter date in 'YYYY-MM-DD' format." in exc_info.value.detail
    )
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_check_genre():
    # Mocking get_movies_genres endpoint
    expected_genres = ["action", "comedy", "romance", "war"]
    with patch(
        "entertainment.routers.movies.get_movies_genres"
    ) as mock_get_movies_genres:
        mock_get_movies_genres.return_value = expected_genres
        logger.debug("\nTEST - Mock called with: %s" % mock_get_movies_genres.call_args)
        logger.debug(
            "\nTEST - Mock return value: %s" % mock_get_movies_genres.return_value
        )

        db_session_generator = override_get_db()
        db_session = next(db_session_generator)

        # Example test case where genres are valid
        await check_genre(db_session, ["action", "comedy"])
        # Ensure that get_movies_genres was awaited correctly
        mock_get_movies_genres.assert_awaited_once_with(db_session)

        # Example test case where genres are invalid
        with pytest.raises(HTTPException) as exc_info:
            await check_genre(db_session, ["romance", "history"])
        assert exc_info.value.status_code == 403
        assert (
            "Invalid genre (check 'get movies genre' for list of accessible genres)"
            in exc_info.value.detail
        )
        # Ensure that get_movies_genres was awaited correctly
        mock_get_movies_genres.assert_awaited_with(db_session)


@pytest.mark.anyio
async def test_get_movies_genres_non_empty_db(
    async_client: AsyncClient, mock_get_movies_genres
):
    # Creating movies with genres in our db
    create_movie(title="First Movie")
    create_movie(title="Second Movie", genres=["comedy", "music", "family"])
    create_movie(title="Third Movie", genres="drama")

    # Making the request to the endpoint
    response = await async_client.get("/movies/genres")

    # Verifying the response status code
    assert response.status_code == 200

    # Verifying that the response body contains the expected genres
    sample_of_expected_genres = ["action", "comedy", "drama"]
    assert sample_of_expected_genres <= response.json()


@pytest.mark.anyio
async def test_add_movie(
    async_client: AsyncClient, created_token: str, mock_get_movies_genres
):
    payload = {
        "title": "Test Movie",
        "premiere": "2022-01-01",  # ISO 8601 formatted string
        "score": 8.5,
        "genres": ["Action", "war"],
        "overview": "Test overview",
        "crew": "Test crew",
        "orig_title": "Original Title",
        "orig_lang": "English",
        "budget": 1000000,
        "revenue": 2000000,
        "country": "US",
    }

    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_(async_client: AsyncClient):
    pass
