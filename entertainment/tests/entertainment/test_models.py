import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from entertainment.enums import EntertainmentCategory
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_books import create_book
from entertainment.tests.utils_games import create_game
from entertainment.tests.utils_movies import create_movie
from entertainment.tests.utils_songs import create_song
from entertainment.tests.utils_users import create_db_user
from entertainment.tests.utils_users_data import create_users_data


@pytest.mark.parametrize(
    "payload, exp_result, model",
    [
        ({"title": "  New title  "}, "New title", "Books"),
        ({"username": "  some user  "}, "some user", "Users"),
        ({"email": "  email@example.com  "}, "email@example.com", "Users"),
    ],
)
def test_strippedstring_class(payload: dict, exp_result: str, model: str):
    if model == "Books":
        result = create_book(**payload)
    else:
        result = create_db_user(**payload)
    assert getattr(result, list(payload.keys())[0]) == exp_result


@pytest.mark.parametrize(
    "title, author, is_error",
    [
        ("New book", "John Doe", True),
        (" new book", "john doe", True),
        (" new Book  ", "  john Doe", True),
        ("Other title", "John Doe", False),
    ],
)
def test_books_unique_title_and_author(title: str, author: str, is_error: bool):
    # Creating a db book with title 'New book' and author 'John Doe'
    create_book(title="New book", author="John Doe")

    # Trying to create a second book record
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            book2 = create_book(title=title, author=author)
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_books_lowercased_title_author'"
            in exc_info._excinfo[1]._message()
        )
    else:
        book2 = create_book(title=title, author=author)
        assert book2.title == title


@pytest.mark.parametrize(
    "title, developer, premiere, is_error",
    [
        ("New game", "Ubisoft", datetime.date(2020, 10, 10), True),
        (" new game", "ubisoft", datetime.date(2020, 10, 10), True),
        (" new Game  ", "  Ubisoft", datetime.date(2020, 10, 10), True),
        ("Other game", "Ubisoft", datetime.date(2020, 10, 10), False),
    ],
)
def test_games_unique_title_and_developer_and_premiere(
    title: str, developer: str, premiere: datetime.date, is_error: bool
):
    # Creating a db game with title 'New game', developer 'Ubisoft' and premiere '2020-10-10'
    create_game(
        title="New game", developer="Ubisoft", premiere=datetime.date(2020, 10, 10)
    )

    # Trying to create a second game record
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            game2 = create_game(title=title, developer=developer, premiere=premiere)
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_games_lowercased_title_premiere_developer'"
            in exc_info._excinfo[1]._message()
        )
    else:
        game2 = create_game(title=title, developer=developer, premiere=premiere)
        assert game2.title == title


@pytest.mark.parametrize(
    "title, premiere, is_error",
    [
        ("New movie", datetime.date(2020, 10, 10), True),
        (" new movie", datetime.date(2020, 10, 10), True),
        (" new Movie  ", datetime.date(2020, 10, 10), True),
        ("Other movie", datetime.date(2020, 10, 10), False),
    ],
)
def test_movies_unique_title_and_premiere(
    title: str, premiere: datetime.date, is_error: bool
):
    # Creating a db movie with title 'New movie', and premiere '2020-10-10'
    create_movie(title="New movie", premiere=datetime.date(2020, 10, 10))

    # Trying to create a second movie record
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            game2 = create_movie(title=title, premiere=premiere)
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_movies_lowercased_title_premiere'"
            in exc_info._excinfo[1]._message()
        )
    else:
        game2 = create_movie(title=title, premiere=premiere)
        assert game2.title == title


@pytest.mark.parametrize(
    "title, artist, album_name, duration, is_error",
    [
        ("New song", "New artist", "New album", 200, True),
        (" new song", "new artist   ", "new album", 200, True),
        (" new song  ", "   New Artist", "   new album  ", 200, True),
        ("Other song", "New artist", "New album", 200, False),
    ],
)
def test_songs_unique_title_and_artist_and_album_name_and_duration(
    title: str, artist: str, album_name: str, duration: int, is_error: bool
):
    create_song(
        title="New song", artist="New artist", album_name="New album", duration_ms=200
    )

    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            create_song(
                title=title, artist=artist, album_name=album_name, duration_ms=duration
            )
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_songs_lowercased_title_artist_album_duration'"
            in exc_info._excinfo[1]._message()
        )
    else:
        song2 = create_song(
            title=title, artist=artist, album_name=album_name, duration_ms=duration
        )
        assert song2.title == title


@pytest.mark.parametrize(
    "username, email, is_error",
    [
        ("testuser", "1@example.com", True),
        (" testuser", "2@example.com", True),
        ("Other user", "3.example.com", False),
    ],
)
def test_user_unique_username(username: str, email: str, is_error: bool):
    # Creating a db user with username 'Testuser'
    create_db_user(username="Testuser", email="test@example.com")

    # Trying to create a second user
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            user2 = create_db_user(username=username, email=email)
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_user_lowercased_username'"
            in exc_info._excinfo[1]._message()
        )
    else:
        user2 = create_db_user(username=username, email=email)
        assert user2.username == username


@pytest.mark.parametrize(
    "category, id_number, is_error",
    [("Books", 1, True), ("Games", 1, True), ("Movies", 1, False), ("Songs", 1, False)],
)
def test_usersdata_unique_category_and_id_number(
    category: str, id_number: int, is_error: bool
):
    # Creating a book, game and movie record
    create_book(title="New book")
    create_game(title="New game")
    create_movie(title="New movie")
    # Creating a users_data for a book and a game
    assessment_book = create_users_data("Books", 1)
    assessment_game = create_users_data("Games", 1)

    # Trying to create a second book and game assessment record
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            assessment2 = create_users_data(category=category, id_number=id_number)
        print(exc_info._excinfo[1]._message())
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: users_data.category, users_data.id_number"
            in exc_info._excinfo[1]._message()
        )
    else:
        assessment2 = create_users_data(category=category, id_number=id_number)
        assert assessment2 is not None


def test_usersdata_get_related_record():
    db = TestingSessionLocal()
    # Creating a book and game record
    book = create_book(title="New book")
    game = create_game(title="New game")
    # Creating a users_data for a book, game and movie
    assessment_book = create_users_data("Books", 1)
    assessment_game = create_users_data("Games", 1)
    assessment_movie = create_users_data("Movies", 1)

    assert assessment_book.get_related_record(db).title == book.title
    assert assessment_game.get_related_record(db).title == game.title
    assert assessment_movie.get_related_record(db) is None


def test_usersdata_object_as_dict():
    book = create_book(title="New book")
    assessment_book = create_users_data("Books", 1)

    # Manually setting the update_timestamp for testing
    assessment_book.update_timestamp = datetime.datetime(
        2020, 10, 10, 15, 15, 15, 150015
    )

    exp_result = {
        "id": 1,
        "category": EntertainmentCategory.BOOKS,
        "id_number": 1,
        "db_record": "New book",
        "finished": False,
        "wishlist": None,
        "watchlist": False,
        "official_rate": None,
        "priv_rate": None,
        "publ_comment": None,
        "priv_notes": None,
        "update_timestamp": datetime.datetime(2020, 10, 10, 15, 15, 15, 150015),
        "created_by": "John_Doe",
    }

    assert assessment_book.object_as_dict() == exp_result
