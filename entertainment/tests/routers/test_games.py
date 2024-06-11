import datetime
from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Games
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_games import create_game, game_payload
from entertainment.tests.utils_users import create_user_and_token


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
async def test_search_games_404_with_empty_db(async_client: AsyncClient):
    response = await async_client.get("games/search")
    assert response.status_code == 404
    assert "Games not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "scenario, query_params, no_of_records, status_code, exp_result",
    [
        ("s1", {"title": "game"}, 2, 200, ["game1", "game3"]),
        ("s2", {"reviews_number": 100}, 3, 200, ["game1", "game2", "game3"]),
        (
            "s3",
            {"reviews_number": 100, "exclude_empty_data": True},
            2,
            200,
            ["game1", "game3"],
        ),
        ("s4", {"developer": "CI", "game_type": "Co-op"}, 2, 200, ["game2", "game4"]),
        ("s5", {"developer": "CI", "review_overall": "Positive"}, 1, 200, ["game4"]),
        ("s6", {"premiere_year": 2020}, 1, 200, ["game3"]),
        ("s7", {"premiere_year": 2012}, 2, 200, ["game1", "game2"]),
        ("s8", {"genres": "casual"}, 1, 200, ["game2"]),
        (
            "s9",
            {
                "reviews_positive": 0.6,
            },
            3,
            200,
            ["game1", "game2", "game4"],
        ),
        (
            "s10",
            {"reviews_positive": 0.6, "order_by": "reviews_number"},
            3,
            200,
            ["game2", "game4", "game1"],
        ),
        (
            "s11",
            {
                "reviews_positive": 0.6,
                "order_by": "reviews_number",
                "order_type": "descending",
            },
            3,
            200,
            ["game1", "game4", "game2"],
        ),
        (
            "s12",
            {"premiere_year": 2012, "game_type": "co-op", "developer": "Ubisoft"},
            0,
            404,
            "Games not found",
        ),
    ],
)
@pytest.mark.anyio
async def test_search_games_scenarios(
    async_client: AsyncClient,
    scenario: str,
    query_params: dict,
    no_of_records: int,
    status_code: int,
    exp_result: list[str] | str,
):
    game1 = create_game(
        "Game 1",
        developer="Ubisoft",
        review_overall="Postive",
        reviews_number=200,
        reviews_positive=0.9,
    )
    game2 = create_game(
        "New title",
        genres=["Casual"],
        game_type="Co-op",
        review_detailed="Negative",
    )
    game3 = create_game(
        premiere=datetime.date(2020, 10, 10),
        publisher="Avalanche",
        reviews_number=600,
        reviews_positive=0.5,
    )
    game4 = create_game(
        "Test",
        datetime.date(2022, 2, 2),
        game_type="Co-op",
        reviews_number=40,
        review_overall="Positive",
    )

    games_mapping = {"game1": game1, "game2": game2, "game3": game3, "game4": game4}

    response = await async_client.get("/games/search", params=query_params)

    assert response.status_code == status_code
    if status_code == 200:
        expected_result = {
            "number_of_games": no_of_records,
            "page": "1 of 1",
            "games": [
                jsonable_encoder(games_mapping[game], exclude_none=True)
                for game in exp_result
                if exp_result
            ],
        }
        assert expected_result == response.json()
    elif status_code == 404:
        assert exp_result in response.json()["detail"]


@pytest.mark.anyio
async def test_search_games_pagination(async_client: AsyncClient):
    # Creating 11 gaees in db
    games = []
    for x in range(1, 12):
        games.append(create_game(title=(str(x) + " game")))

    # Calling the endpoint for the second page with all games
    expected_result = {
        "number_of_games": 11,
        "page": "2 of 2",
        "games": [jsonable_encoder(games[-1], exclude_none=True)],
    }
    response = await async_client.get(
        "/games/search", params={"title": "game", "page_number": 2}
    )
    assert response.status_code == 200
    assert expected_result == response.json()

    # Calling the endpoint for the second page with game title '3 game'
    expected_result = "Games not found."
    response = await async_client.get(
        "/games/search", params={"title": "3 game", "page_number": 2}
    )
    assert response.status_code == 404
    assert expected_result == response.json()["detail"]


@pytest.mark.anyio
async def test_add_game_201(async_client: AsyncClient, created_token: str):
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
async def test_add_game_401_if_not_authorized(async_client: AsyncClient):
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
async def test_add_game_422_not_unique_game(
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
async def test_add_game_422_invalid_input_data(
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


@pytest.mark.anyio
async def test_update_game_200(
    async_client: AsyncClient, added_game: Games, created_token: str
):
    payload = {"publisher": "    Ubisoft"}
    assert added_game.id == 1
    assert added_game.publisher != payload["publisher"]
    assert added_game.updated_by is None

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["publisher"] == "Ubisoft"
    assert response.json()["updated_by"] == "testuser"


@pytest.mark.anyio
async def test_update_game_401_if_not_authenticated(
    async_client: AsyncClient, added_game: Games
):
    payload = {"publisher": "Ubisoft"}

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_game_404_if_book_not_found(
    async_client: AsyncClient, added_game: Games, created_token: str
):
    payload = {"publisher": "Ubisoft"}

    response = await async_client.patch(
        f"/games/invalid/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "The record was not found in the database" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_game_200_update_by_the_admin(
    async_client: AsyncClient, added_game: Games
):
    assert added_game.created_by == "testuser"

    user, token = create_user_and_token(username="admin_user", role="admin")
    payload = {"publisher": "Ubisoft"}

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "testuser" in response.json()["created_by"]
    assert "admin_user" in response.json()["updated_by"]


@pytest.mark.anyio
async def test_update_game_403_update_by_the_user_who_is_not_the_book_creator_nor_admin(
    async_client: AsyncClient, added_game: Games
):
    assert added_game.created_by == "testuser"

    user, token = create_user_and_token(username="some_user", role="user")
    payload = {"publisher": "Ubisoft"}

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
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
async def test_update_game_422_not_unique_game(
    async_client: AsyncClient, added_game: Games, created_token: str
):
    create_game("New game", datetime.date(2011, 11, 11), "some developer")

    payload = {"developer": "some developer"}

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert "UNIQUE constraint failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_game_400_if_no_data_to_change(
    async_client: AsyncClient, added_game: Games, created_token: str
):
    payload = {"genres": [None, None], "game_type": [None, None]}

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 400
    assert "No data input provided" in response.json()["detail"]


@pytest.mark.parametrize(
    "payload, exp_response",
    [
        ({"genres": ["invalid"]}, "Invalid genres"),
        ({"game_type": ["invalid"]}, "Invalid game_type"),
        ({"premiere": "10-10-2020"}, "Input should be a valid date or datetime"),
        (
            {"review_overall": "invalid"},
            "Input should be 'Negative', 'Mixed' or 'Positive'",
        ),
        ({"review_detailed": "invalid"}, "Input should be 'Very Negative'"),
        ({"reviews_positive": 11}, "Input should be less than or equal to 1"),
    ],
)
@pytest.mark.anyio
async def test_update_game_422_incorrect_update_data(
    async_client: AsyncClient,
    added_game: Games,
    created_token: str,
    payload: dict,
    exp_response: str,
):
    payload = payload

    response = await async_client.patch(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert exp_response in response.text


@pytest.mark.parametrize(
    "title, developer",
    [
        ("New game", "Avalanche Studios"),
        ("NEW Game", "Avalanche STUDIOs"),
        ("    New game  ", "  Avalanche Studios  "),
    ],
)
@pytest.mark.anyio
async def test_delete_game_204(
    async_client: AsyncClient,
    added_game: Games,
    created_token: str,
    title: str,
    developer: str,
):
    game = (
        TestingSessionLocal()
        .query(Games)
        .filter(
            Games.title == added_game.title,
            Games.developer == added_game.developer,
            Games.premiere == added_game.premiere,
        )
        .first()
    )
    assert game is not None

    response = await async_client.delete(
        f"/games/{title}/{added_game.premiere}/{developer}",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 204
    game = (
        TestingSessionLocal()
        .query(Games)
        .filter(
            Games.title == added_game.title,
            Games.developer == added_game.developer,
            Games.premiere == added_game.premiere,
        )
        .first()
    )
    assert game is None


@pytest.mark.anyio
async def test_delete_game_401_if_not_authenticated(
    async_client: AsyncClient,
    added_game: Games,
):
    response = await async_client.delete(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_game_404_if_game_not_found(
    async_client: AsyncClient, added_game: Games, created_token: str
):
    response = await async_client.delete(
        f"/games/invalid/{added_game.premiere}/{added_game.developer}",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        f"The record was not found in the database. Searched game: invalid ({added_game.premiere}) by {added_game.developer}"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_delete_game_204_if_deleted_by_admin(
    async_client: AsyncClient,
    added_game: Games,
):
    user, token = create_user_and_token("admin_user", role="admin")
    assert added_game.created_by != user.username

    response = await async_client.delete(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
    game = (
        TestingSessionLocal()
        .query(Games)
        .filter(
            Games.title == added_game.title,
            Games.developer == added_game.developer,
            Games.premiere == added_game.premiere,
        )
        .first()
    )
    assert game is None


@pytest.mark.anyio
async def test_delete_game_403_forbidden_if_not_admin_or_game_creator(
    async_client: AsyncClient,
    added_game: Games,
):
    user, token = create_user_and_token("some_user", role="user")
    assert added_game.created_by != user.username

    response = await async_client.delete(
        f"/games/{added_game.title}/{added_game.premiere}/{added_game.developer}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the database record "
        "can change or delete the record from the database" in response.text
    )
    game = (
        TestingSessionLocal()
        .query(Games)
        .filter(
            Games.title == added_game.title,
            Games.developer == added_game.developer,
            Games.premiere == added_game.premiere,
        )
        .first()
    )
    assert game is not None
