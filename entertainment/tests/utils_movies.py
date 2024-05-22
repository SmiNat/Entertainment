import logging
from datetime import datetime

from entertainment.models import Movies
from entertainment.tests.conftest import TestingSessionLocal

logger = logging.getLogger(__name__)


def movie_payload(
    title: str = "Test Movie",
    premiere: str = "2011-11-11",  # ISO 8601 formatted string
    score: float | None = 8.5,
    genres: list[str] | None = ["Action", "war"],
    overview: str | None = "Test overview",
    crew: str | None = "Test crew",
    orig_title: str | None = None,
    orig_lang: str | None = "English",
    budget: int | float | None = None,
    revenue: int | float | None = None,
    country: str | None = "US",
) -> dict:
    payload = {
        "title": title,
        "premiere": premiere,
        "score": score,
        "genres": genres,
        "overview": overview,
        "crew": crew,
        "orig_title": orig_title,
        "orig_lang": orig_lang,
        "budget": budget,
        "revenue": revenue,
        "country": country,
    }
    return payload


def create_movie(
    title: str = "Test Movie",
    premiere: str = "2011-11-11",  # ISO 8601 formatted string
    score: float | None = 8.5,
    genres: list[str] | None = ["Action", "Mystery"],
    overview: str | None = None,
    crew: str | None = "Test crew",
    orig_title: str | None = None,
    orig_lang: str | None = "Spanish",
    budget: int | float | None = None,
    revenue: int | float | None = None,
    country: str | None = "ES",
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


def check_if_db_movies_table_is_not_empty() -> bool:
    db = TestingSessionLocal()
    db_content = db.query(Movies).all()
    if db_content:
        return True
    return False
