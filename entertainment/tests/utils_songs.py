import datetime

from entertainment.models import Songs
from entertainment.tests.conftest import TestingSessionLocal


def create_song(
    song_id: str | None = None,
    title: str = "New song",
    artist: str = "Nw atrist",
    song_popularity: int | None = 80,
    album_id: str | None = None,
    album_name: str = "New album",
    album_premiere: datetime.date | None = datetime.date(2020, 10, 10),
    playlist_name: str = "New album",
    playlist_genre: str | None = "rock",
    playlist_subgenre: str | None = "hard rock",
    duration_ms: int | None = 247600,
    created_by: str = "John_Doe",
):
    song = Songs(
        song_id=song_id,
        title=title,
        artist=artist,
        song_popularity=song_popularity,
        album_id=album_id,
        album_name=album_name,
        album_premiere=album_premiere,
        playlist_name=playlist_name,
        playlist_genre=playlist_genre,
        playlist_subgenre=playlist_subgenre,
        duration_ms=duration_ms,
        created_by=created_by,
    )
    db = TestingSessionLocal()

    try:
        db.add(song)
        db.commit()
        db.refresh(song)
        return song
    finally:
        db.close()
