from entertainment.enums import EntertainmentCategory
from entertainment.models import UsersData
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_books import create_book
from entertainment.tests.utils_movies import create_movie


def assessment_payload(
    category: str = "Books",
    id_number: int = 1,
    finished: bool = False,
    wishlist: str | None = "ASAP",
    watchlist: bool = True,
    official_rate: str | int | None = None,
    priv_rate: str | None = "Masterpiece",
    priv_notes: str | None = "Ok, worth spend time on",
    publ_comment: str | None = None,
) -> dict:
    payload = {
        "category": category,
        "id_number": id_number,
        "finished": finished,
        "wishlist": wishlist,
        "watchlist": watchlist,
        "official_rate": official_rate,
        "priv_rate": priv_rate,
        "priv_notes": priv_notes,
        "publ_comment": publ_comment,
    }
    return payload


def create_users_data(
    category: str = EntertainmentCategory.BOOKS,
    id_number: int = 1,
    db_record: str = "New book",
    finished: bool = False,
    wishlist: str | None = None,
    watchlist: bool = False,
    official_rate: str | int | None = None,
    priv_rate: str | None = None,
    priv_notes: str | None = None,
    publ_comment: str | None = None,
    created_by: str | None = "John_Doe",
):
    users_data = UsersData(
        category=category,
        id_number=id_number,
        db_record=db_record,
        finished=finished,
        wishlist=wishlist,
        watchlist=watchlist,
        official_rate=official_rate,
        priv_rate=priv_rate,
        priv_notes=priv_notes,
        publ_comment=publ_comment,
        created_by=created_by,
    )

    try:
        db = TestingSessionLocal()
        db.add(users_data)
        db.commit()
        db.refresh(users_data)
        return users_data
    finally:
        db.close()


def populate_database():
    create_book(title="Book1", created_by="testuser")
    create_book(title="Book2", created_by="testuser")
    create_book(title="Book3", created_by="testuser")
    create_book(title="Book4")
    create_movie(title="Movie1", created_by="testuser")
    assessment1 = create_users_data(
        category="Books",
        id_number=1,
        db_record="Book1",
        watchlist=True,
        priv_rate="Awesome",
        created_by="testuser",
    )
    assessment2 = create_users_data(
        category="Books",
        id_number=2,
        db_record="Book2",
        finished=True,
        official_rate=3,
        wishlist="Maybe someday",
        created_by="testuser",
    )
    assessment3 = create_users_data(
        category="Books",
        id_number=3,
        db_record="Book4",
        priv_rate="Awesome",
        created_by="John_Doe",
    )
    assessment4 = create_users_data(
        category="Movies",
        id_number=1,
        db_record="Movie1",
        priv_rate="Awesome",
        official_rate="3",
        created_by="testuser",
    )
    return assessment1, assessment2, assessment3, assessment4
