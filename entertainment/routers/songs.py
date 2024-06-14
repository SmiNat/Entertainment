import datetime
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
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
    song_popularity: int | None = Field(default=None, le=0, ge=100, examples=[None])
    album_id: str | None = Field(default=None, examples=[None])
    album_name: str
    album_premiere: datetime.date | None = Field(default=None, examples=[None])
    playlist_name: str | None = Field(default=None, examples=[None])
    playlist_genre: str | None = Field(default=None, examples=[None])
    playlist_subgenre: str
    duration_ms: int | None = Field(default=None, gt=0, examples=[None])


@router.get("/get_playlist_genres", status_code=200)
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
    return result
