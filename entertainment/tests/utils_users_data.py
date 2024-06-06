from entertainment.enums import EntertainmentCategory
from entertainment.models import UsersData
from entertainment.tests.conftest import TestingSessionLocal


def create_users_data(
    category: str = EntertainmentCategory.BOOKS,
    id_number: int = 1,
    finished: bool = False,
    wishlist: str | None = None,
    watchlist: bool = False,
    vote: str | None = None,
    notes: str | None = None,
):
    users_data = UsersData(
        category=category,
        id_number=id_number,
        finished=finished,
        wishlist=wishlist,
        watchlist=watchlist,
        vote=vote,
        notes=notes,
    )
    try:
        db = TestingSessionLocal()
        db.add(users_data)
        db.commit()
        db.refresh(users_data)
        return users_data
    finally:
        db.close()
