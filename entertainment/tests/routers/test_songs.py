from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Songs
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_songs import create_song, song_payload
from entertainment.tests.utils_users import create_user_and_token


@pytest.mark.anyio
async def test_get_playlist_genres_empty_db(async_client: AsyncClient):
    exp_result = {"genres": [], "subgenres": {}}
    response = await async_client.get("songs/genres")
    assert response.status_code == 200
    assert exp_result == response.json()


@pytest.mark.anyio
async def test_get_playlist_genres_200(async_client: AsyncClient):
    create_song(title="Song 1", playlist_genre="pop", playlist_subgenre="electropop")
    create_song(title="Song 2", playlist_genre="rap", playlist_subgenre="trap")
    create_song(title="Song 3", playlist_genre="rap", playlist_subgenre="hip hop")
    create_song(title="Song 4", playlist_genre="rap", playlist_subgenre="hip hop")
    create_song(title="Song 5", playlist_genre="rock", playlist_subgenre="classic rock")

    exp_result = {
        "genres": ["pop", "rap", "rock"],
        "subgenres": {
            "pop": ["electropop"],
            "rap": ["hip hop", "trap"],
            "rock": ["classic rock"],
        },
    }
    response = await async_client.get("songs/genres")
    assert response.status_code == 200
    assert exp_result == response.json()


@pytest.mark.anyio
async def test_get_all_songs_200(async_client: AsyncClient):
    song1 = create_song(
        title="Song 1", playlist_genre="pop", playlist_subgenre="electropop"
    )
    song2 = create_song(title="Song 2", playlist_genre="rap", playlist_subgenre="trap")
    song3 = create_song(
        title="Song 3", playlist_genre="rap", playlist_subgenre="hip hop"
    )

    exp_response = {
        "number_of_songs": 3,
        "page": "1 of 1",
        "songs": [
            jsonable_encoder(song1, exclude_none=True),
            jsonable_encoder(song2, exclude_none=True),
            jsonable_encoder(song3, exclude_none=True),
        ],
    }

    response = await async_client.get("songs/all")
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.anyio
async def test_get_all_songs_404_with_empty_db(async_client: AsyncClient):
    response = await async_client.get("songs/all")
    assert response.status_code == 404
    assert "Songs not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_all_songs_200_pagination(async_client: AsyncClient):
    song1 = create_song(title="Song 1")
    song2 = create_song(title="Song 2")
    song3 = create_song(title="Song 3")

    exp_response = {
        "number_of_songs": 3,
        "page": "2 of 2",
        "songs": [
            jsonable_encoder(song3, exclude_none=True),
        ],
    }

    response = await async_client.get(
        "songs/all", params={"page_number": 2, "page_size": 2}
    )
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.anyio
async def test_get_all_songs_404_pagination_with_empty_content(
    async_client: AsyncClient,
):
    song1 = create_song(title="Song 1")
    song2 = create_song(title="Song 2")
    song3 = create_song(title="Song 3")

    response = await async_client.get(
        "songs/all", params={"page_number": 2, "page_size": 5}
    )
    assert response.status_code == 404
    assert "Songs not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "scenario, params, no_of_songs, songs",
    [
        ("no params", {}, 3, ["song1", "song2", "song3"]),
        ("all songs", {"title": "song "}, 3, ["song1", "song2", "song3"]),
        ("rock songs", {"playlist_genre": "rock"}, 2, ["song1", "song3"]),
        ("artist 'Doe", {"artist": "Doe"}, 2, ["song1", "song3"]),
        ("classic rock songs", {"playlist_subgenre": "classic rock"}, 1, ["song3"]),
        ("album name", {"album_name": "album"}, 2, ["song2", "song3"]),
        ("mix", {"playlist_genre": "rock", "album_name": "album"}, 1, ["song3"]),
    ],
)
@pytest.mark.anyio
async def test_search_songs_200(
    async_client: AsyncClient,
    scenario: str,
    params: dict,
    no_of_songs: int,
    songs: list,
):
    song1 = create_song(title="Song 1", album_name="XYZ", artist="doe")
    song2 = create_song(title="Song 2", playlist_genre="pop")
    song3 = create_song(
        title="Song 3", artist="John Doe", playlist_subgenre="classic rock"
    )

    songs_mapping = {"song1": song1, "song2": song2, "song3": song3}

    exp_response = {
        "number_of_songs": no_of_songs,
        "page": "1 of 1",
        "songs": list(
            jsonable_encoder(songs_mapping[song], exclude_none=True) for song in songs
        ),
    }
    response = await async_client.get("songs/search", params=params)
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.anyio
async def test_search_songs_404(async_client: AsyncClient):
    song1 = create_song(title="Song 1", album_name="XYZ", artist="doe")
    song2 = create_song(title="Song 2", playlist_genre="pop")
    song3 = create_song(title="Song 3")

    exp_response = "Songs not found"
    response = await async_client.get("songs/search", params={"title": "invalid"})
    assert response.status_code == 404
    assert exp_response in response.json()["detail"]


@pytest.mark.anyio
async def test_search_songs_404_if_invalid_page_number(async_client: AsyncClient):
    song1 = create_song(title="Song 1", album_name="XYZ", artist="doe")
    song2 = create_song(title="Song 2", playlist_genre="pop")
    song3 = create_song(title="Song 3")

    # Valid page number
    response = await async_client.get("songs/search", params={"page_number": 1})
    assert response.status_code == 200

    # Invalid page number
    exp_response = "Songs not found"
    response = await async_client.get("songs/search", params={"page_number": 999})
    assert response.status_code == 404
    assert exp_response in response.json()["detail"]


@pytest.mark.anyio
async def test_add_song_201(async_client: AsyncClient, created_token: str):
    payload = song_payload()

    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_data:
        mocked_data.return_value = ["rock", "hard rock"]
        response = await async_client.post(
            "/songs/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 201
        assert "New song" == response.json()["title"]
        assert "testuser" == response.json()["created_by"]


@pytest.mark.anyio
async def test_add_song_401_if_not_authorized(async_client: AsyncClient):
    payload = song_payload()

    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_data:
        mocked_data.return_value = ["rock", "hard rock"]
        response = await async_client.post("/songs/add", json=payload)
        assert response.status_code == 401
        assert "Not authenticated" == response.json()["detail"]


@pytest.mark.anyio
async def test_add_song_422_not_unique_song(
    async_client: AsyncClient, created_token: str, added_song: Songs
):
    payload = song_payload(
        title=added_song.title,
        artist=added_song.artist,
        album_name=added_song.album_name,
    )

    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_data:
        mocked_data.return_value = ["rock", "hard rock"]
        response = await async_client.post(
            "/songs/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert (
            "A song with that title, artist and album name already exists in the database"
            in response.json()["detail"]
        )


@pytest.mark.parametrize(
    "invalid_key, invalid_value, expected_response",
    [
        ("title", None, "Input should be a valid string"),
        (
            "album_premiere",
            "2020, 10, 10",
            "Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'.",
        ),
        (
            "album_premiere",
            "202",
            "Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'.",
        ),
        (
            "album_premiere",
            "2020-40-10",
            "Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'.",
        ),
        (
            "playlist_genre",
            "invalid",
            "Invalid 'playlist_genre': check 'genres' for list of accessible 'playlist_genre'",
        ),
        (
            "playlist_subgenre",
            "invalid",
            "Invalid 'playlist_subgenre' for rock genre: check 'genres' for list of accessible 'playlist_subgenre'",
        ),
        ("duration_ms", -8, "Input should be greater than 0"),
        ("song_popularity", -8, "Input should be greater than or equal to 0"),
    ],
)
@pytest.mark.anyio
async def test_add_song_422_invalid_input_data(
    async_client: AsyncClient,
    created_token: str,
    invalid_key: str,
    invalid_value: str | list | int | float | None,
    expected_response: str,
):
    payload = song_payload()
    payload[invalid_key] = invalid_value

    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_data:
        mocked_data.return_value = ["rock", "hard rock"]
        response = await async_client.post(
            "/songs/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert expected_response in response.text


@pytest.mark.anyio
async def test_add_song_invalid_subgenre_with_no_genre(
    async_client: AsyncClient, created_token: str
):
    payload = song_payload(playlist_genre=None, playlist_subgenre="invalid")
    response = await async_client.post(
        "/songs/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert (
        "Invalid 'playlist_subgenre': check 'genres' for list of accessible 'playlist_subgenre'"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_add_song_subgenre_without_genre(
    async_client: AsyncClient, created_token: str
):
    payload = song_payload(playlist_subgenre="dance pop", playlist_genre=None)
    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_subgenre:
        mocked_subgenre.return_value = ["dance pop", "electropop"]
        with patch("entertainment.routers.songs.get_genre_by_subgenre") as mocked_genre:
            mocked_genre.return_value = "pop"
            response = await async_client.post(
                "/songs/add",
                json=payload,
                headers={"Authorization": f"Bearer {created_token}"},
            )
            assert response.status_code == 201
            assert (
                response.json()["playlist_genre"] == "pop"
            )  # added by the endpoint mechanism


@pytest.mark.anyio
async def test_update_song_200(
    async_client: AsyncClient, added_song: Songs, created_token: str
):
    payload = {"artist": "      New artist"}
    assert added_song.id == 1
    assert added_song.artist != payload["artist"]
    assert added_song.updated_by is None

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["artist"] == "New artist"
    assert response.json()["updated_by"] == "testuser"


@pytest.mark.anyio
async def test_update_song_401_if_not_authenticated(
    async_client: AsyncClient, added_song: Songs
):
    payload = {"artist": "New"}

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_song_404_if_song_not_found(
    async_client: AsyncClient, added_song: Songs, created_token: str
):
    payload = {"artist": "New"}

    response = await async_client.patch(
        f"/songs/update/invalid/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "The record was not found in the database" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_song_200_update_by_the_admin(
    async_client: AsyncClient, added_song: Songs
):
    assert added_song.created_by == "testuser"

    user, token = create_user_and_token(username="admin_user", role="admin")
    payload = {"artist": "New"}

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "testuser" in response.json()["created_by"]
    assert "admin_user" in response.json()["updated_by"]


@pytest.mark.anyio
async def test_update_song_403_update_by_the_user_who_is_not_the_song_creator_nor_admin(
    async_client: AsyncClient, added_song: Songs
):
    assert added_song.created_by == "testuser"

    user, token = create_user_and_token(username="some_user", role="user")
    payload = {"artist": "New"}

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the "
        "database record can change or delete the record from the database"
        in response.text
    )


@pytest.mark.anyio
async def test_update_song_422_not_unique_song(
    async_client: AsyncClient, added_song: Songs, created_token: str
):
    create_song(title="A song", artist="Song artist", album_name="Abc album")

    payload = {"album_name": "Abc album"}

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert "UNIQUE constraint failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_song_400_if_no_data_to_change(
    async_client: AsyncClient, added_song: Songs, created_token: str
):
    payload = {}

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 400
    assert "No data input provided" in response.json()["detail"]


@pytest.mark.parametrize(
    "case, payload, exp_response",
    [
        (
            "invalid genre with old subgenre",
            {"playlist_genre": "rap"},
            "Invalid new genre with old subgenre. Accessible subgenres for 'rap' genre: [",
        ),
        (
            "invalid subgenre",
            {"playlist_subgenre": "invalid"},
            "Invalid subgenre: check 'genres' for list of accessible subgenres",
        ),
        (
            "invalid subgenre (hard rock) for new genre (rap)",
            {"playlist_subgenre": "hard rock", "playlist_genre": "rap"},
            "Invalid subgenre for given genre. Accessible subgenres for 'rap' genre: [",
        ),
        (
            "invalid new genre (rap) for old subgenre (dance pop)",
            {"playlist_genre": "rap"},
            "Invalid new genre with old subgenre. Accessible subgenres for 'rap' genre: [",
        ),
        (
            "invalid album year",
            {"album_premiere": "999"},
            "Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'",
        ),
        (
            "invalid album date",
            {"album_premiere": "10-10-2020"},
            "Invalid date format. Enter date in 'YYYY-MM-DD' or 'YYYY'",
        ),
        (
            "invalid popularity",
            {"song_popularity": -8},
            "Input should be greater than or equal to 0",
        ),
        ("invalid duration", {"duration_ms": -11}, "Input should be greater than 0"),
    ],
)
@pytest.mark.anyio
async def test_update_song_422_incorrect_update_data(
    async_client: AsyncClient,
    added_song: Songs,
    created_token: str,
    payload: dict,
    exp_response: str,
    case: str,
):
    payload = payload

    response = await async_client.patch(
        f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert exp_response in response.text


@pytest.mark.anyio
async def test_update_song_422_if_invalid_subgenre_with_old_genre(
    async_client: AsyncClient,
    created_token: str,
    added_song: Songs,
):
    payload = {"playlist_subgenre": "hard rock"}
    with patch("entertainment.routers.songs.get_unique_row_data") as mocked_subgenres:
        mocked_subgenres.return_value = [
            "classic rock",
            "hard rock",
            "electropop",
            "dance pop",
        ]
        with patch("entertainment.routers.songs.get_genre_by_subgenre") as mocked_genre:
            mocked_genre.return_value = "rock"
            response = await async_client.patch(
                f"/songs/update/{added_song.title}/{added_song.artist}/{added_song.album_name}",
                json=payload,
                headers={"Authorization": f"Bearer {created_token}"},
            )
            assert response.status_code == 422
            assert (
                "Invalid subgenre for song's genre. Update genre for 'rock' or change subgenre"
                in response.json()["detail"]
            )


@pytest.mark.anyio
async def test_update_song_422_if_invalid_genre(
    async_client: AsyncClient, created_token: str
):
    song = create_song(
        playlist_genre=None, playlist_subgenre=None, created_by="testuser"
    )
    payload = {"playlist_genre": "invalid"}

    response = await async_client.patch(
        f"/songs/update/{song.title}/{song.artist}/{song.album_name}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert (
        "Invalid genre: check 'genres' for list of accessible genres"
        in response.json()["detail"]
    )


@pytest.mark.parametrize(
    "title, artist",
    [
        ("A song", "Song artist"),
        ("     a song", "SONG Artist"),
        ("    A Song  ", "  song artist  "),
    ],
)
@pytest.mark.anyio
async def test_delete_song_204(
    async_client: AsyncClient,
    added_song: Songs,
    created_token: str,
    title: str,
    artist: str,
):
    song = (
        TestingSessionLocal()
        .query(Songs)
        .filter(
            Songs.title == added_song.title,
            Songs.artist == added_song.artist,
            Songs.album_name == added_song.album_name,
        )
        .first()
    )
    assert song is not None

    response = await async_client.delete(
        f"/songs/delete/{title}/{artist}/{added_song.album_name}",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 204
    song = (
        TestingSessionLocal()
        .query(Songs)
        .filter(
            Songs.title == added_song.title,
            Songs.artist == added_song.artist,
            Songs.album_name == added_song.album_name,
        )
        .first()
    )
    assert song is None


@pytest.mark.anyio
async def test_delete_song_401_if_not_authenticated(
    async_client: AsyncClient,
    added_song: Songs,
):
    response = await async_client.delete(
        f"/songs/delete/{added_song.title}/{added_song.artist}/{added_song.album_name}",
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_song_404_if_song_not_found(
    async_client: AsyncClient, added_song: Songs, created_token: str
):
    response = await async_client.delete(
        f"/songs/delete/invalid/{added_song.artist}/{added_song.album_name}",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        f"The record was not found in the database. Searched song: invalid by {added_song.artist} (album: {added_song.album_name})"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_delete_song_204_if_deleted_by_admin(
    async_client: AsyncClient,
    added_song: Songs,
):
    user, token = create_user_and_token("admin_user", role="admin")
    assert added_song.created_by != user.username

    response = await async_client.delete(
        f"/songs/delete/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
    song = (
        TestingSessionLocal()
        .query(Songs)
        .filter(
            Songs.title == added_song.title,
            Songs.album_name == added_song.album_name,
            Songs.artist == added_song.artist,
        )
        .first()
    )
    assert song is None


@pytest.mark.anyio
async def test_delete_song_403_forbidden_if_not_admin_or_song_creator(
    async_client: AsyncClient,
    added_song: Songs,
):
    user, token = create_user_and_token("some_user", role="user")
    assert added_song.created_by != user.username

    response = await async_client.delete(
        f"/songs/delete/{added_song.title}/{added_song.artist}/{added_song.album_name}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the database record "
        "can change or delete the record from the database" in response.text
    )
    song = (
        TestingSessionLocal()
        .query(Songs)
        .filter(
            Songs.title == added_song.title,
            Songs.album_name == added_song.album_name,
            Songs.artist == added_song.artist,
        )
        .first()
    )
    assert song is not None
