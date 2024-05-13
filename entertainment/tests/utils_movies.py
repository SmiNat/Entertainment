from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from entertainment.models import Movies
from entertainment.tests.conftest import TestingSessionLocal

MOVIE_GENRES = [
    "action",
    "adventure",
    "animation",
    "comedy",
    "crime",
    "documentary",
    "drama",
    "family",
    "fantasy",
    "history",
    "horror",
    "music",
    "mystery",
    "romance",
    "science fiction",
    "thriller",
    "tv movie",
    "war",
    "western",
]


@pytest.fixture
def mock_get_movies_genres():
    with patch(
        "entertainment.routers.movies.get_movies_genres"
    ) as mock_get_movies_genres:
        mock_get_movies_genres.return_value = MOVIE_GENRES
        yield mock_get_movies_genres


def create_movie(
    title: str | None = "Test Movie",
    premiere: str | None = "2011-11-11",  # ISO 8601 formatted string
    score: float | None = 8.5,
    genres: list[str] | None = ["Action"],
    overview: str | None = None,
    crew: str | None = "Test crew",
    orig_title: str | None = None,
    orig_lang: str | None = "English",
    budget: int | float | None = None,
    revenue: int | float | None = None,
    country: str | None = "US",
    created_by: str | None = "John_Doe",
):
    if isinstance(premiere, str):
        premiere = datetime.strptime(premiere, "%Y-%m-%d").date()
    if isinstance(genres, list):
        genres = ", ".join(genres)

    movie = Movies(
        title=title,
        premiere=premiere,
        score=score,
        genres=genres,
        overview=overview,
        crew=crew,
        orig_title=orig_title,
        orig_lang=orig_lang,
        budget=budget,
        revenue=revenue,
        country=country,
        created_by=created_by,
    )

    db = TestingSessionLocal()
    try:
        db.add(movie)
        db.commit()
        db.refresh(movie)
        return movie
    finally:
        # db.execute(text("DELETE FROM movies"))
        # db.commit()
        db.close()


async def add_movie(
    payload: dict | None, async_client: AsyncClient, created_token: str
):
    if not payload:
        payload = {
            "title": "New movie",
            "premiere": "2022-12-12",
            "score": 888,
            "genres": ["action", "horror"],
            "overview": None,
            "crew": "Big Star, No Name",
            "orig_title": "New movie",
            "orig_lang": "ENG",
            "budget": None,
            "revenue": None,
            "country": "Poland",
        }
    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    return response.json()


@pytest.fixture()
async def added_movie(async_client: AsyncClient, created_token: str):
    """Creates movie record in the database before running a test."""
    return await add_movie(async_client, created_token)
