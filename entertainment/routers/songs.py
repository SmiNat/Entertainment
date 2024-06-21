import datetime
import logging
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.models import Songs
from entertainment.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs", tags=["songs"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class SongRequest(BaseModel):
    song_id: str | None = Field(default=None, examples=[None])
    title: str
    artist: str
    song_popularity: int | None = Field(default=None, ge=0, le=100, examples=[None])
    album_id: str | None = Field(default=None, examples=[None])
    album_name: str
    album_premiere: datetime.date | None = Field(default=None, examples=[None])
    playlist_name: str | None = Field(default=None, examples=[None])
    playlist_genre: list[str] | None = Field(default=None, examples=[None])
    playlist_subgenre: list[str] | None = Field(default=None, examples=[None])
    duration_ms: int | None = Field(default=None, gt=0, examples=[None])


class SongResponse(SongRequest):
    playlist_genre: str | None
    playlist_subgenre: str | None
    id: int
    created_by: str | None
    updated_by: str | None

    class DictConfig:
        from_attributes = True


class UpdateSongRequest(SongRequest):
    title: str | None = Field(default=None, examples=[None])
    artit: str | None = Field(default=None, examples=[None])
    album_name: str | None = Field(default=None, examples=[None])


class ResponseModel(BaseModel):
    number_of_songs: int
    page: str
    songs: list[SongResponse]


@router.get("/genres", status_code=200)
async def get_playlist_genres(db: db_dependency):
    data = db.query(Songs.playlist_genre, Songs.playlist_subgenre).distinct().all()

    result = {"genres": [], "subgenres": {}}

    for genre, subgenre in data:
        if genre not in result["genres"]:
            result["genres"].append(genre)
            result["subgenres"][genre] = []
            result["subgenres"][genre].append(subgenre)
        if subgenre not in result["subgenres"][genre]:
            result["subgenres"][genre].append(subgenre)

    result["genres"] = sorted(result["genres"])
    for subgenre in list(result["subgenres"].keys()):
        result["subgenres"][subgenre] = sorted(result["subgenres"][subgenre])

    return result


@router.get(
    "/all",
    status_code=200,
    response_model=ResponseModel,
    response_model_exclude_none=True,
)
async def get_all_songs(
    db: db_dependency,
    page_number: int = Query(gt=0, default=1),
    page_size: int = Query(
        default=10, gt=0, le=100, description="Number of records per page."
    ),
):
    songs = db.query(Songs)
    results = songs.offset((page_number - 1) * page_size).limit(page_size).all()
    if not results:
        raise HTTPException(404, "Songs not found.")

    response = {
        "number_of_songs": songs.count(),
        "page": f"{page_number} of {ceil(songs.count()/page_size)}",
        "songs": results,
    }

    return response
