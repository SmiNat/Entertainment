import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.tests.utils_songs import create_song


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
