import datetime


def create_game(
    title: str = "Test game",
    premiere: datetime.date = datetime.datetime(2011, 11, 11),
    developer: str = "EA Games",
    publisher: str | None = "EA Games",
    genres: list[str] = ["Action", "RPG", "Strategy"],
    type: list[str] | None = ["Multi-Player", "MMO"],
    price_eur: float | None = 1.5,
    price_discounted_eur: float | None = None,
    review_overall: str | None = "Mixed",
    review_detailed: str | None = "Mostly Positive",
    reviews_number: int | None = None,
    reviews_positive: float | None = 0.8,
):
    pass
