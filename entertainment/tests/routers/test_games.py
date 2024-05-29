from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.tests.utils_games import create_game


@pytest.mark.anyio
async def test_get_choices_200(async_client: AsyncClient):
    with patch("entertainment.routers.games.get_unique_row_data") as mocked_value:
        mocked_value.return_value = ["Action", "Casual", "RPG"]
        result = await async_client.get(
            "/games/get_choices", params={"field": "genres"}
        )
        assert result.status_code == 200
        assert ["Action", "Casual", "RPG"] == result.json()


@pytest.mark.anyio
async def test_get_all_games_200(async_client: AsyncClient):
    game1 = create_game("Game 1")
    game2 = create_game("Game 2", price_eur=4.5)
    game3 = create_game("Game 3", publisher="CI Games")
    expected_result = {
        "number_of_games": 3,
        "page": "1 of 1",
        "games": [
            jsonable_encoder(game1, exclude_none=True),
            jsonable_encoder(game2, exclude_none=True),
            jsonable_encoder(game3, exclude_none=True),
        ],
    }

    response = await async_client.get("/games/all")
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_games_404_no_games(async_client: AsyncClient):
    response = await async_client.get("/games/all")
    assert response.status_code == 404
    assert "Games not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "page_size, page_number, page, exp_result, status_code",
    [
        (10, 1, "1 of 1", ["game1", "game2", "game3"], 200),
        (2, 1, "1 of 2", ["game1", "game2"], 200),
        (2, 2, "2 of 2", ["game3"], 200),
    ],
)
@pytest.mark.anyio
async def test_get_all_game_200_with_pagination(
    async_client: AsyncClient,
    page_size: int,
    page_number: int,
    page: str | None,
    exp_result: list[str] | None,
    status_code: int,
):
    game1 = create_game("Game 1")
    game2 = create_game("Game 2", price_eur=4.5)
    game3 = create_game("Game 3", publisher="CI Games")
    all_games = {"game1": game1, "game2": game2, "game3": game3}

    expected_result = {
        "number_of_games": 3,
        "page": page,
        "games": [
            jsonable_encoder(all_games[x], exclude_none=True) for x in exp_result
        ],
    }

    response = await async_client.get(
        "/games/all", params={"page_size": page_size, "page_number": page_number}
    )
    assert response.status_code == status_code
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_game_404_with_pagination(
    async_client: AsyncClient,
):
    create_game("Game 1")
    create_game("Game 2", price_eur=4.5)
    create_game("Game 3", publisher="CI Games")

    response = await async_client.get(
        "/games/all", params={"page_size": 2, "page_number": 4}
    )
    assert response.status_code == 404
    assert "Games not found" in response.json()["detail"]
