import datetime
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Row, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql._typing import _TP
from starlette import status

from entertainment.database import get_db
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import Movies
from entertainment.routers.auth import get_current_user
from entertainment.routers.utils import (
    check_country,
    check_date,
    check_if_author_or_admin,
    check_items_list,
    check_language,
    convert_items_list_to_a_sorted_string,
    convert_list_to_unique_values,
    get_unique_row_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/movies", tags=["movies"], responses={404: {"description": "Not found."}}
)


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

if __name__ == "__main__":
    accessible_movie_genres = get_unique_row_data(
        os.environ.get("DEV_DATABASE_PATH"), "movies", "genres"
    )


class MovieRequest(BaseModel):
    title: str
    premiere: datetime.date = Field(description="YYYY-MM-DD format.")
    score: float = Field(default=0, ge=0, le=10, description="IMDB score.")
    genres: list[str] = Field(max_length=500)
    overview: str | None = Field(default=None, max_length=500, examples=[None])
    crew: str | None = Field(default=None, max_length=500, examples=[None])
    orig_title: str | None = Field(
        default=None, max_length=200, examples=[None], description="Original title."
    )
    orig_lang: str | None = Field(
        default=None, max_length=30, examples=[None], description="Original language."
    )
    budget: float | None = Field(default=None, ge=0, examples=[None])
    revenue: float | None = Field(default=None, ge=0, examples=[None])
    country: str | None = Field(default=None, max_length=30, examples=[None])

    class ConfigDict:
        from_attributes = True

    @field_validator("orig_lang")
    @classmethod
    def language_is_in_pycountry_library(cls, lang: str):
        return check_language(lang)

    @field_validator("country")
    @classmethod
    def country_is_in_pycountry_library(cls, country: str):
        return check_country(country)

    @field_validator("genres")
    @classmethod
    def genres_are_valid_and_converted_to_a_string(cls, genres: list):
        return (
            check_items_list(genres, accessible_movie_genres)
            if isinstance(genres, list)
            else genres
        )


class MovieResponse(MovieRequest):
    genres: str
    id: int
    created_by: str | None
    updated_by: str | None

    class ConfigDict:
        from_attributes = True


class UpdateMovieRequest(MovieRequest):
    title: str | None = Field(default=None, examples=[None])
    premiere: datetime.date | None = Field(
        default=None, description="YYYY-MM-DD format.", examples=[None]
    )
    score: float | None = Field(
        default=None, ge=0, le=10, description="IMDB score.", examples=[None]
    )
    genres: list[str | None] | None = Field(
        default=None,
        max_length=500,
        examples=[[None, None]],
        description="Provide genres as a list.",
    )


class UserDataRequest(BaseModel):
    # data_id = Column(Integer, primary_key=True, index=True, unique=True)
    finished: bool = False
    vote: int = Field(default=None, ge=0, le=10)
    notes: str = Field(default=None, max_length=500)
    # create_timestamp = Column(DateTime, default=datetime.datetime.now())
    # update_timestamp = Column(DateTime, default=datetime.datetime.now(),
    #                           onupdate=datetime.datetime.now())
    # user_id = Column(UUID, ForeignKey("users.user_id"))
    # movie_id = Column(Integer, ForeignKey("movies.index"))


@router.get("/genres", status_code=200, description="Get all available movie genres.")
async def get_movies_genres(db: db_dependency) -> list:
    query = select(Movies.genres).distinct()
    genres = db.execute(query).scalars().all()
    unique_genres = convert_list_to_unique_values(genres)
    logger.debug("Number of available movie genres: %s." % len(unique_genres))
    return unique_genres


@router.get(
    "/all",
    response_model=None,
    status_code=200,
    description="Get all movies stored in the database.",
)
async def get_all_movies(
    db: db_dependency,
    page_size: int = Query(10, ge=1, le=100),
    page_number: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:
    movie_model = db.query(Movies).all()

    if not movie_model:
        raise RecordNotFoundException(detail="Movies not found.")

    logger.debug("Database hits (all movies): %s records." % len(movie_model))

    start_index = (page_number - 1) * page_size
    end_index = start_index + page_size

    return {
        "number of movies": len(movie_model),
        "movies": movie_model[start_index:end_index],
    }


@router.get(
    "/search",
    response_model=None,
    status_code=200,
    description="Search movies stored in the database.",
)
async def search_movies(
    db: db_dependency,
    title: str = "",
    premiere_since: str = Query(
        default="1900-1-1", description="Use YYYY-MM-DD, eg. 2024-07-12."
    ),
    premiere_before: str = Query(
        default="2050-1-1", description="Use YYYY-MM-DD, eg. 2024-07-12."
    ),
    score_ge: float = Query(default=0, ge=0, le=10),
    genre_primary: str | None = None,
    genre_secondary: str | None = None,
    country: str | None = None,
    language: str | None = None,
    crew: str | None = None,
    exclude_empty_data: bool = Query(
        default=False,
        description="To exclude from search records with empty score.",
    ),
    page: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:
    check_date(premiere_before)
    check_date(premiere_since)

    query = db.query(Movies).filter(
        Movies.premiere >= premiere_since,
        Movies.premiere <= premiere_before,
        Movies.title.icontains(title),
    )

    if exclude_empty_data:
        query = query.filter(Movies.score >= score_ge)
    else:
        query = query.filter(or_(Movies.score >= score_ge, Movies.score.is_(None)))

    if crew is not None:
        query = query.filter(Movies.crew.icontains(crew))
    if genre_primary is not None:
        query = query.filter(Movies.genres.icontains(genre_primary))
    if genre_secondary is not None:
        query = query.filter(Movies.genres.icontains(genre_secondary))
    if country is not None:
        query = query.filter(Movies.country.icontains(country))
    if language is not None:
        query = query.filter(Movies.orig_lang.icontains(language))

    logger.debug("Database hits (search movies): %s." % len(query.all()))

    results = query.offset((page - 1) * 10).limit(10).all()
    return {"number of movies": len(query.all()), "movies": results}


@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_movie(
    db: db_dependency, user: user_dependency, movie_request: MovieRequest
):
    movie = Movies(**movie_request.model_dump(), created_by=user.get("username"))
    genres = convert_items_list_to_a_sorted_string(movie_request.genres)
    movie.genres = genres

    try:
        db.add(movie)
        db.commit()
        db.refresh(movie)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A movie with that title and that premiere date already exists in the database."
        )

    logger.debug(
        "Movie: '%s' was successfully added to database by the '%s' user."
        % (movie.title, user["username"])
    )

    return movie


@router.patch("/{title}/{premiere}", status_code=202)
async def update_movie(
    db: db_dependency,
    user: user_dependency,
    movie_update: UpdateMovieRequest,
    title: str,
    premiere: datetime.date = Path(description="Use YYYY-MM-DD, eg. 2024-07-12."),
):
    """Update movie - endpoint available for user who created a movie record or for an admin user."""

    logger.debug("Movie to update: '%s' (%s)." % (title, premiere))

    movie = (
        db.query(Movies)
        .filter(
            Movies.premiere == premiere,
            func.lower(Movies.title) == title.strip().casefold(),
        )
        .first()
    )
    if movie is None:
        raise RecordNotFoundException(
            extra_data=f"Searched movie: '{title}' ({premiere})."
        )

    # Verify if user is authorized to update a movie
    check_if_author_or_admin(user, movie)

    fields_to_update = movie_update.model_dump(exclude_unset=True, exclude_none=True)
    if not fields_to_update:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="No data input provided."
        )
    logger.debug("Fields to update: %s" % fields_to_update)

    try:
        for field, value in fields_to_update.items():
            logger.debug("Updating: field: %s, value: %s" % (field, value))
            if field == "genres":
                setattr(movie, field, convert_items_list_to_a_sorted_string(value))
            else:
                setattr(movie, field, value)
        movie.updated_by = user["username"]
        db.commit()
        db.refresh(movie)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A movie with that title and that premiere date already exists in the database."
        )

    logger.debug(
        "Movie '%s' (%s) was successfully updated by the '%s' user."
        % (title, premiere, user["username"])
    )

    return movie


@router.delete("/{title}/{premiere}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    title: str, premiere: str, db: db_dependency, user: user_dependency
):
    logger.debug("Movie to delete: '%s' (%s)." % (title, premiere))

    movie = (
        db.query(Movies)
        .filter(
            Movies.premiere == premiere,
            func.lower(Movies.title) == title.strip().casefold(),
        )
        .first()
    )
    if movie is None:
        raise RecordNotFoundException(
            extra_data=f"Searched movie: '{title}' ({premiere})."
        )

    # Verify if user is authorised to update a movie
    check_if_author_or_admin(user, movie)

    db.delete(movie)
    db.commit()

    logger.debug(
        "Movie '%s' (%s) was successfully deleted by the '%s' user."
        % (movie.title, movie.premiere, user["username"])
    )
