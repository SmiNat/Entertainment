import datetime

from entertainment.models import Games
from entertainment.routers.utils import convert_items_list_to_a_sorted_string
from entertainment.tests.conftest import TestingSessionLocal


def create_game(
    title: str = "Test game",
    premiere: datetime.date = datetime.datetime(2011, 11, 11),
    developer: str = "EA Games",
    publisher: str | None = "EA Games",
    genres: list[str] = ["Action", "RPG", "Strategy"],
    game_type: list[str] | None = ["Multi-Player", "MMO"],
    price_eur: float | None = 1.5,
    price_discounted_eur: float | None = None,
    review_overall: str | None = "Mixed",
    review_detailed: str | None = "Mostly Positive",
    reviews_number: int | None = None,
    reviews_positive: float | None = 0.8,
):
    if isinstance(genres, list):
        genres = convert_items_list_to_a_sorted_string(genres)
    if isinstance(game_type, list):
        game_type = convert_items_list_to_a_sorted_string(game_type)

    game = Games(
        title=title,
        premiere=premiere,
        developer=developer,
        publisher=publisher,
        genres=genres,
        type=game_type,
        price_eur=price_eur,
        price_discounted_eur=price_discounted_eur,
        review_overall=review_overall,
        review_detailed=review_detailed,
        reviews_number=reviews_number,
        reviews_positive=reviews_positive,
    )

    db = TestingSessionLocal()
    try:
        db.add(game)
        db.commit()
        db.refresh(game)
        return game
    finally:
        db.close()
