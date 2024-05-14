import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import Row, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql._typing import _TP
from starlette import status

from entertainment.database import get_db
from entertainment.enums import MovieGenres
from entertainment.exceptions import DatabaseError
from entertainment.models import Movies, Users

from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/movies", tags=["movies"], responses={404: {"description": "Not found."}}
)


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def check_date(date_value: str, format: str = "%Y-%m-%d") -> None:
    try:
        datetime.datetime.strptime(date_value, format).date()
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid date type. Enter date in 'YYYY-MM-DD' format.",
        )


def check_genre(genres: list[str]):
    accessible_genres = list(map(lambda genre: genre.value, MovieGenres))
    for genre in genres:
        if genre.lower() in accessible_genres:
            continue
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Invalid genre (check 'get movies genres' for list of accessible genres).",
            )


class MovieRequest(BaseModel):
    title: str
    premiere: datetime.date = Field(description="YYYY-MM-DD format.")
    score: float = Field(default=0, ge=0, le=10, description="IMDB score.")
    genres: list[str] = Field(max_length=500)
    overview: str | None = Field(default=None, max_length=500, examples=[None])
    crew: str | None = Field(default=None, max_length=500, examples=[None])
    orig_title: str | None = Field(default=None, max_length=200, examples=[None])
    orig_lang: str | None = Field(default=None, max_length=30, examples=[None])
    budget: float | None = Field(default=None, ge=0, examples=[None])
    revenue: float | None = Field(default=None, ge=0, examples=[None])
    country: str | None = Field(default=None, max_length=3, examples=[None])

    class ConfigDict:
        from_attributes = True


class MovieResponse(MovieRequest):
    id: int
    created_by: str
    updated_by: str

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
    unique_genres = set()
    for element in genres:
        if element:
            if "," not in element:
                unique_genres.add(element.lower())
            else:
                genre_list = element.split(",")
                for genre in genre_list:
                    genre = str(genre).strip()
                    unique_genres.add(genre.lower())
    logger.debug(
        "GET movies genres - number of available movie genres: %s." % len(unique_genres)
    )
    return sorted(unique_genres)


@router.get(
    "/all",
    response_model=None,
    status_code=200,
    description="Get all movies stored in the database.",
)
async def get_all_movies(
    db: db_dependency,
    page_size: int = Query(10, ge=1, le=100),
    page: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:
    movie_model = db.query(Movies).all()

    if movie_model is None:
        raise HTTPException(status_code=404, detail="Movies not found.")

    logger.debug("GET all movies - database hits: %s records." % len(movie_model))

    start_index = (page - 1) * page_size
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
    premiere_since: str = Query(default="1900-1-1", description="Use yyyy-mm-dd."),
    premiere_before: str = Query(default="2050-1-1", description="Use yyyy-mm-dd."),
    score_ge: float = Query(default=0, ge=0, le=10),
    genre_primary: str | None = None,
    genre_secondary: str | None = None,
    country: str | None = None,
    language: str | None = None,
    crew: str | None = None,
    page: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:
    check_date(premiere_before)
    check_date(premiere_since)

    query = db.query(Movies).filter(
        Movies.premiere >= premiere_since,
        Movies.premiere <= premiere_before,
        Movies.score >= score_ge,
        Movies.title.icontains(title),
    )

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

    if query is None:
        raise HTTPException(status_code=404, detail="Movie not found.")

    logger.debug("GET search movies - database hits: %s." % len(query.all()))

    results = query.offset((page - 1) * 10).limit(10).all()
    return {"number of movies": len(query.all()), "movies": results}


@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_movie(
    db: db_dependency, user: user_dependency, movie_request: MovieRequest
):
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Could not validate credentials."
        )

    check_movie_in_db = (
        db.query(Movies)
        .filter(
            Movies.title == movie_request.title,
            Movies.premiere == movie_request.premiere,
        )
        .first()
    )

    if check_movie_in_db:
        raise HTTPException(
            status.HTTP_405_METHOD_NOT_ALLOWED,
            f"Movie '{movie_request.title}' is already registered in the database.",
        )

    genre_list = movie_request.genres
    check_genre(genre_list)
    genres = ", ".join(genre_list)

    movie_model = Movies(**movie_request.model_dump(), created_by=user.get("username"))
    movie_model.genres = genres

    db.add(movie_model)
    db.commit()

    logger.debug(
        "POST on add movie: '%s' successfully added to database." % movie_model.title
    )


@router.patch("/update/{title}/{premiere}", status_code=202)
async def update_movie(
    title: str,
    premiere: str,
    db: db_dependency,
    user: user_dependency,
    movie_update: UpdateMovieRequest,
):
    """Update movie - endpoint available for user who created a movie record or for an admin user."""
    check_date(premiere)

    # Movie to update
    movie = (
        db.query(Movies)
        .filter(
            Movies.premiere == premiere,
            func.lower(Movies.title) == title.strip().casefold(),
        )
        .first()
    )
    logger.debug("Update movie: title='%s', premiere='%s" % (title, premiere))
    logger.debug("Movie found: %s" % jsonable_encoder(movie))

    if movie is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Movie '{title}' ({premiere}) not found in the database.",
        )

    # Fields to update
    updated_fields = movie_update.model_dump(exclude_unset=True, exclude_none=True)
    logger.debug("Fields to update: %s" % updated_fields)

    # Converting 'genres' field from a list to a string of valid (available) genres
    if "genres" in updated_fields.keys():
        # Removing None values from the genres list
        genres = [item.strip() for item in updated_fields["genres"] if item]
        if genres:
            logger.debug("Genres: %s" % genres)
            # Verifying if genres are on the list of available genres
            check_genre(genres)
            # Converting a list to a string
            genres = ", ".join(genres)
            logger.debug("Genres final: %s" % genres)
        else:
            del updated_fields["genres"]
            logger.debug("Fields to update final: %s" % updated_fields)

    if not updated_fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="No data input provided."
        )

    # Movie update available only for movie 'created_by' the authenticated_user
    # or for admin user
    authenticated_user = db.query(Users).filter(Users.id == user["id"]).first()

    if not (
        authenticated_user.role == "admin"
        or authenticated_user.username == movie.created_by
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Only admin or author of a movie record can update a movie.",
        )
    else:
        try:
            for field, value in updated_fields.items():
                logger.debug("field, value: %s %s" % (field, value))
                if field == "genres":
                    setattr(movie, field, genres)
                else:
                    setattr(movie, field, value)
            movie.updated_by = authenticated_user.username
            db.commit()
            db.refresh(movie)
        except IntegrityError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=f"{DatabaseError(e._message())}"
            )

    logger.debug(
        "Movie %s (%s) was successfully updated by the '%s' user."
        % (title, premiere, authenticated_user.username)
    )

    return movie
