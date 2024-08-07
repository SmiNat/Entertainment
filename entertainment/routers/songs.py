import logging
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import SongGenres
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import Songs
from entertainment.routers.auth import get_current_user
from entertainment.utils import (
    check_date,
    check_if_author_or_admin,
    get_genre_by_subgenre,
    get_unique_row_data,
)

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
    album_premiere: str | None = Field(default=None, examples=[None])
    playlist_name: str | None = Field(default=None, examples=[None])
    playlist_genre: str | None = Field(default=None, examples=[None])
    playlist_subgenre: str | None = Field(default=None, examples=[None])
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
    artist: str | None = Field(default=None, examples=[None])
    album_name: str | None = Field(default=None, examples=[None])

    class DictConfig:
        from_attributes = True


class ResponseModel(BaseModel):
    number_of_songs: int
    page: str
    songs: list[SongResponse]


@router.get("/genres", status_code=200)
async def get_playlist_genres(db: db_dependency):
    data = db.query(Songs.playlist_genre, Songs.playlist_subgenre).distinct().all()

    result = {"genres": [], "subgenres": {}}

    for genre, subgenre in data:
        if genre and genre not in result["genres"]:
            result["genres"].append(genre)
            result["subgenres"][genre] = []
            result["subgenres"][genre].append(subgenre)
        if subgenre and subgenre not in result["subgenres"][genre]:
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


@router.get(
    "/search",
    status_code=200,
    response_model=ResponseModel,
    response_model_exclude_none=True,
)
async def search_songs(
    db: db_dependency,
    title: str | None = None,
    artist: str | None = None,
    album_name: str | None = None,
    popularity: int | None = Query(
        default=None, ge=0, le=100, description="Index number between 0 and 100."
    ),
    playlist_genre: str | None = Query(default=None, enum=SongGenres.list_of_values()),
    playlist_subgenre: str | None = None,
    page_number: int = Query(1, ge=1),
):
    params = locals().copy()

    icontains_fields = [
        "title",
        "artist",
        "album_name",
        "playlist_genre",
        "playlist_subgenre",
    ]

    songs = db.query(Songs)

    for attr in params:
        if attr in icontains_fields and params[attr]:
            songs = songs.filter(getattr(Songs, attr).icontains(params[attr].strip()))

    if popularity:
        songs = songs.filter(
            or_(Songs.song_popularity >= popularity, Songs.song_popularity.is_(None))
        )
    logger.debug("Database hits (search songs): %s." % len(songs.all()))

    try:
        results = songs.offset((page_number - 1) * 10).limit(10).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not results:
        raise HTTPException(404, "Songs not found.")

    return {
        "number_of_songs": songs.count(),
        "page": f"{page_number} of {ceil(songs.count()/10)}",
        "songs": results,
    }


@router.post("/add", status_code=201, response_model=SongResponse)
async def add_song(
    db: db_dependency, user: user_dependency, new_song: SongRequest
) -> Songs:
    all_fields = new_song.model_dump()

    # Validate premiere date (year or full date)
    if all_fields["album_premiere"]:
        if not (
            not all_fields["album_premiere"].isdigit()
            and len(all_fields["album_premiere"]) == 4
        ):
            check_date(
                all_fields["album_premiere"],
                error_message="Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'.",
            )

    # Validate playlist_genre field
    genre = all_fields.get("playlist_genre", None)
    if genre:
        genre = genre.strip().lower()
        accessible_options = get_unique_row_data(
            db, "songs", "playlist_genre", case_type="lower"
        )
        if genre not in accessible_options:
            raise HTTPException(
                422,
                "Invalid 'playlist_genre': check 'genres' for list of accessible 'playlist_genre'.",
            )
        all_fields["playlist_genre"] = genre

    # Validate playlist_subgenre field
    subgenre = all_fields.get("playlist_subgenre", None)
    if subgenre:
        subgenre = subgenre.strip().lower()
        # Subgenre without genre
        if not genre:
            accessible_options = get_unique_row_data(
                db, "songs", "playlist_subgenre", case_type="lower"
            )
            if subgenre not in accessible_options:
                raise HTTPException(
                    422,
                    "Invalid 'playlist_subgenre': check 'genres' for list of accessible 'playlist_subgenre'.",
                )
            genre = get_genre_by_subgenre(
                db,
                "songs",
                "playlist_genre",
                "playlist_subgenre",
                subgenre,
            )
            all_fields["playlist_genre"] = genre
        # Subgenre with genre
        else:
            accessible_options = get_unique_row_data(
                db,
                "songs",
                "playlist_genre",
                "playlist_subgenre",
                genre,
                "lower",
            )
            if subgenre not in accessible_options:
                raise HTTPException(
                    422,
                    f"Invalid 'playlist_subgenre' for {genre} genre: check 'genres' for list of accessible 'playlist_subgenre'.",
                )
        all_fields["playlist_subgenre"] = subgenre

    song = Songs(**all_fields, created_by=user["username"])

    try:
        db.add(song)
        db.commit()
        db.refresh(song)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A song with that title, artist and album name already exists in the database."
        )

    logger.debug(
        "Song: '%s' was successfully added to database by the '%s' user."
        % (song.title, user["username"])
    )
    return song


@router.patch("/{title}/{artist}/{album}", status_code=200)
async def update_song(
    db: db_dependency,
    user: user_dependency,
    title: str,
    artist: str,
    album: str,
    song_update: UpdateSongRequest,
):
    song = (
        db.query(Songs)
        .filter(
            func.lower(Songs.title) == title.strip().casefold(),
            func.lower(Songs.artist) == artist.strip().casefold(),
            func.lower(Songs.album_name) == album.strip().casefold(),
        )
        .first()
    )
    if not song:
        raise RecordNotFoundException(
            extra_data=f"Searched song: '{title}' by {artist} (album: {album})."
        )

    # Verify if user is authorized to update a song
    check_if_author_or_admin(user, song)

    # Get all fields to update
    fields_to_validate = song_update.model_dump(exclude_unset=True, exclude_none=True)
    fields_to_update = fields_to_validate.copy()

    if not fields_to_update:
        raise HTTPException(400, detail="No data input provided.")
    logger.debug("Fields to update: %s" % fields_to_update)

    # Validate genre and subgenre fields
    old_genre = song.playlist_genre
    old_subgenre = song.playlist_subgenre
    new_genre = fields_to_update.get("playlist_genre", None)
    new_subgenre = fields_to_update.get("playlist_subgenre", None)

    if not new_genre and not new_subgenre:
        pass
    else:
        accessible_genres = get_unique_row_data(
            db, "songs", "playlist_genre", case_type="lower"
        )
        if new_genre and not new_subgenre and not old_subgenre:
            if new_genre.strip().lower() not in accessible_genres:
                raise HTTPException(
                    422, "Invalid genre: check 'genres' for list of accessible genres."
                )
        elif new_genre:
            accessible_subgenres = get_unique_row_data(
                db,
                "songs",
                "playlist_genre",
                "playlist_subgenre",
                new_genre.strip().lower(),
                case_type="lower",
            )
            if new_subgenre:
                if new_subgenre.strip().lower() not in accessible_subgenres:
                    raise HTTPException(
                        422,
                        f"Invalid subgenre for given genre. Accessible subgenres for '{new_genre.strip().lower()}' genre: {accessible_subgenres}.",
                    )
                fields_to_update["playlist_subgenre"] = new_subgenre.strip().lower()
            elif old_subgenre:
                if old_subgenre.strip().lower() not in accessible_subgenres:
                    raise HTTPException(
                        422,
                        f"Invalid new genre with old subgenre. Accessible subgenres for '{new_genre.strip().lower()}' genre: {accessible_subgenres}.",
                    )
            fields_to_update["playlist_genre"] = new_genre.strip().lower()
        elif new_subgenre and not new_genre:
            all_accessible_subgenres = get_unique_row_data(
                db,
                "songs",
                "playlist_subgenre",
                case_type="lower",
            )
            if new_subgenre.strip().lower() not in all_accessible_subgenres:
                raise HTTPException(
                    422,
                    "Invalid subgenre: check 'genres' for list of accessible subgenres.",
                )
            genre = get_genre_by_subgenre(
                db,
                "songs",
                "playlist_genre",
                "playlist_subgenre",
                new_subgenre.strip().lower(),
            )
            if not old_genre:
                fields_to_update["playlist_genre"] = genre
            elif old_genre.strip().lower() != genre:
                raise HTTPException(
                    422,
                    f"Invalid subgenre for song's genre. Update genre for '{genre}' or change subgenre.",
                )
            fields_to_update["playlist_subgenre"] = new_subgenre.strip().lower()

    # Update fields
    for field, value in fields_to_update.items():
        logger.debug("Updating: field: %s, value: %s" % (field, value))

        # Validate premiere date (year or full date)
        if field == "album_premiere":
            if not (value.isdigit() and len(value) == 4):
                check_date(
                    value,
                    error_message="Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'.",
                )

        setattr(song, field, value.strip())
    song.updated_by = user["username"]

    # Insert changes into the database
    try:
        db.commit()
        db.refresh(song)
    except IntegrityError as e:
        raise DatabaseIntegrityError(detail=str(e.orig))

    logger.debug(
        "Song: '%s' was successfully updated by the '%s' user."
        % (song.title, user["username"])
    )
    return song


@router.delete("/{title}/{artist}/{album}", status_code=204)
async def delete_song(
    db: db_dependency,
    user: user_dependency,
    title: str,
    artist: str,
    album: str,
):
    logger.debug("Song to delete: '%s' (%s) by %s." % (title, artist, album))

    song = (
        db.query(Songs)
        .filter(
            func.lower(Songs.title) == title.strip().lower(),
            func.lower(Songs.artist) == artist.strip().lower(),
            func.lower(Songs.album_name) == album.strip().lower(),
        )
        .first()
    )
    if not song:
        raise RecordNotFoundException(
            extra_data=f"Searched song: {title} by {artist} (album: {album})."
        )

    # Verify if user is authorized to delete a song
    check_if_author_or_admin(user, song)

    db.delete(song)
    db.commit()

    logger.debug(
        "Song '%s' (%s) by %s was successfully deleted by the '%s' user."
        % (title, album, artist, user["username"])
    )
