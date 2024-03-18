import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Annotated
from sqlalchemy import and_, or_, Row, select
from sqlalchemy.orm import Session
from sqlalchemy.sql._typing import _TP
from starlette import status

from database import SessionLocal
from models import Movies, UserData


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        # logging.FileHandler("debug.log"),
        logging.StreamHandler()]
)

router = APIRouter(
    prefix="/movies",
    tags=["movies"],
    responses={404: {"description": "Not found."}}
)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
# userdata_dependency = Annotated[Session, Depends(get_db)]
# user_dependency = Annotated[dict, Depends(get_current_user)]  # okodować


def check_date(date_value: str, format: str = "%Y-%m-%d") -> None:
    try:
        datetime.datetime.strptime(date_value, format).date()
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Invalid date type. Enter date in YYYY-MM-DD "
                            "format.")


class MoviesRequest(BaseModel):

    title: str
    premiere: datetime.date = Field(description="YYYY-MM-DD format.")
    score: float = Field(default=0, ge=0, le=1000)
    genre: list = Field(max_length=500)
    overview: str = Field(max_length=500)
    crew: str = Field(max_length=500)
    orig_title: str = Field(default=None, max_length=200)
    orig_lang: str = Field(default=None, max_length=30)
    budget: float = Field(default=None, ge=0)
    revenue: float = Field(default=None,ge=0)
    country: str = Field(default=None, max_length=3)


class MoviesResponse(MoviesRequest):

    index: int
    created_by: str
    updated_by: str


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


test_db = [{"title": "Creed III", "year": 2020, "stars": "Sylvester Stalone"},
           {"title": "Titanic", "year": 1980, "stars": "Leonardo DiCaprio, Kate Winslet"}]


@router.get("/test_all")
async def get_all():
    return test_db


@router.get("/test_search")
async def get_test(title: str):
    for element in test_db:
        if title.lower() in element["title"].lower():
            return element


@router.get("/genres", description="Get all available movie genres.")
def get_movies_genre(db: db_dependency) -> set:
    query = select(Movies.genre).distinct()
    genres = db.execute(query).scalars().all()
    unique_genres = set()
    for element in genres:
        if element:
            if "," not in element:
                unique_genres.add(element)
            else:
                genre_list = element.split(",")
                for genre in genre_list:
                    genre = str(genre).strip()
                    unique_genres.add(genre)
    logging.info("✅ Number of available movie genres: %s." %len(unique_genres))
    return unique_genres


@router.get("/all", response_model=None, status_code=200,
            description="Get all movies stored in the database.")
async def get_all_movies(
        db: db_dependency,
        page_size: int = Query(10, ge=1, le=100),
        page: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:
    movie_model = db.query(Movies).all()

    if movie_model is None:
        raise HTTPException(status_code=404, detail='Movie not found.')

    logging.info("✅ Database hits: %s records." %len(movie_model))

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    return {"number of movies": len(movie_model),
            "movies": movie_model[start_index:end_index]}


@router.get("/search", response_model=None, status_code=200,
            description="Search movies stored in the database.")
async def search_movies(
        db: db_dependency,
        title: str = "",
        country: str = "",
        premiere_since: str = Query(
            default="1900-1-1", description="Use yyyy-mm-dd."),
        premiere_before: str = Query(
            default="2050-1-1", description="Use yyyy-mm-dd."),
        score_ge: float = Query(default=0, ge=0, le=10),
        genre_primary: str | None = None,
        genre_secondary: str | None = None,
        crew: str | None = None,
        page: int = Query(default=1, gt=0),
) -> dict[str, list[Row[_TP]]]:

    check_date(premiere_before)
    check_date(premiere_since)

    query = db.query(Movies).filter(
        Movies.premiere >= premiere_since,
        Movies.premiere <= premiere_before,
        Movies.score >= score_ge,
        Movies.title.contains(title),
        Movies.country.contains(country),
    )

    if crew is not None:
        query = query.filter(Movies.crew.contains(crew))
    if genre_primary is not None:
        query = query.filter(Movies.genre.contains(genre_primary))
    if genre_secondary is not None:
        query = query.filter(Movies.genre.contains(genre_secondary))

    if query is None:
        raise HTTPException(status_code=404, detail='Movie not found.')

    logging.info("✅ Database hits: %s." %len(query.all()))

    results = query.offset((page - 1) * 10).limit(10).all()
    return {"number of movies": len(query.all()), "movies": results}





# @router.post("/add")
# async def add_movie(db: db_dependency, ):
    # zlikwidować duplikaty w index w movies db
    # primary keys
    # timestamp
    # foreign keys
    # check movie genre
        # casefold
        # in list
        # (comma saparated if more than 1)

