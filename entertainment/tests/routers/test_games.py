from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Games
from entertainment.tests.utils_games import create_game, game_payload


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


@pytest.mark.anyio
async def test_add_book_201(async_client: AsyncClient, created_token: str):
    payload = game_payload()

    with patch("entertainment.routers.games.get_unique_row_data") as mocked_data:
        mocked_data.return_value = [
            "Action",
            "RPG",
            "Strategy",
            "Co-op",
            "Multi-player",
            "MMO",
        ]
        response = await async_client.post(
            "/games/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 201
        assert "New game" == response.json()["title"]
        assert "testuser" == response.json()["created_by"]


@pytest.mark.anyio
async def test_add_book_401_if_not_authorized(async_client: AsyncClient):
    payload = game_payload()

    with patch("entertainment.routers.games.get_unique_row_data") as mocked_data:
        mocked_data.return_value = [
            "Action",
            "RPG",
            "Strategy",
            "Co-op",
            "Multi-player",
            "MMO",
        ]
        response = await async_client.post("/games/add", json=payload)
        assert response.status_code == 401
        assert "Not authenticated" == response.json()["detail"]


@pytest.mark.anyio
async def test_add_book_422_not_unique_game(
    async_client: AsyncClient, created_token: str, added_game: Games
):
    payload = game_payload(
        title=added_game.title,
        premiere=added_game.premiere.strftime("%Y-%m-%d"),
        developer=added_game.developer,
    )

    with patch("entertainment.routers.games.get_unique_row_data") as mocked_data:
        mocked_data.return_value = [
            "Action",
            "RPG",
            "Strategy",
            "Co-op",
            "Multi-player",
            "MMO",
        ]
        response = await async_client.post(
            "/games/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert (
            "A game with that title, premiere date and developer already exists in the database"
            in response.json()["detail"]
        )


@pytest.mark.parametrize(
    "invalid_key, invalid_value, expected_response",
    [
        ("title", None, "Input should be a valid string"),
        ("premiere", "2020, 10, 10", "invalid date separator, expected `-`"),
        ("premiere", "2020-40-10", "month value is outside expected range of 1-12"),
        ("genres", [None, None], "Input should be a valid string"),
        (
            "genres",
            ["invalid", "Action"],
            "Invalid genres: check 'get choices' for list of accessible genres",
        ),
        (
            "game_type",
            ["invalid", "Co-op"],
            "Invalid game_type: check 'get choices' for list of accessible game_type",
        ),
        ("price_discounted_eur", "ten", "Input should be a valid number"),
        ("price_discounted_eur", -8, "Input should be greater than or equal to 0"),
        ("review_overall", "Cool", "Input should be 'Negative', 'Mixed' or 'Positive"),
        (
            "review_detailed",
            "Very Cool",
            "Input should be 'Very Negative', 'Negative', 'Mostly Negative'",
        ),
        ("reviews_positive", -8, "Input should be greater than or equal to 0"),
    ],
)
@pytest.mark.anyio
async def test_add_movie_422_invalid_input_data(
    async_client: AsyncClient,
    created_token: str,
    invalid_key: str,
    invalid_value: str | list | int | float | None,
    expected_response: str,
):
    payload = game_payload()
    payload[invalid_key] = invalid_value

    with patch("entertainment.routers.games.get_unique_row_data") as mocked_data:
        mocked_data.return_value = [
            "Action",
            "RPG",
            "Strategy",
            "Co-op",
            "Multi-player",
            "MMO",
        ]
        response = await async_client.post(
            "/games/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert expected_response in response.text
