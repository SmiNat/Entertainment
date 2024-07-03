from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Songs
from entertainment.tests.utils_songs import create_song, song_payload


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
            "Invalid date type. Enter date in 'YYYY-MM-DD' format",
        ),
        (
            "album_premiere",
            "202",
            "Invalid date type. Enter date in 'YYYY-MM-DD' format",
        ),
        (
            "album_premiere",
            "2020-40-10",
            "Invalid date type. Enter date in 'YYYY-MM-DD' format",
        ),
        (
            "playlist_genre",
            "invalid",
            "Invalid 'playlist_genre': check 'genres' for list of accessible 'playlist_genre'",
        ),
        (
            "playlist_subgenre",
            "invalid",
            "Invalid 'playlist_subgenre': check 'genres' for list of accessible 'playlist_subgenre'",
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
