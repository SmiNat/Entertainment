import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from entertainment.tests.utils_books import create_book
from entertainment.tests.utils_games import create_game
from entertainment.tests.utils_movies import create_movie
from entertainment.tests.utils_users import create_db_user


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
        ("New song", "Some artist", "Album 1", 200, True),
        (" new song", "some artist   ", "album 1", 200, True),
        (" new song  ", "   Some Artist", "   album 1  ", 200, True),
        ("Other song", "Some artist", "Album 1", 200, False),
    ],
)
def test_songs_unique_title_and_artist_and_album_name_and_duration(
    title: str, artist: str, album_name: str, duration: int, is_error: bool
):
    assert False


@pytest.mark.parametrize(
    "username,  is_error",
    [
        ("testuser", True),
        (" testuser", True),
        ("Other user", False),
    ],
)
def test_user_unique_username(username: str, is_error: bool):
    # Creating a db user with username 'Testuser'
    create_db_user(username="Testuser")

    # Trying to create a second user
    if is_error:
        with pytest.raises(IntegrityError) as exc_info:
            user2 = create_db_user(username=username)
        assert (
            "(sqlite3.IntegrityError) UNIQUE constraint failed: index 'idx_user_lowercased_username'"
            in exc_info._excinfo[1]._message()
        )
    else:
        user2 = create_db_user(username=username, email="other@email.com")
        assert user2.username == username


@pytest.mark.parametrize(
    "category, id_number, is_error",
    [("Books", 1, False), ("Games", 1, False), ("Movies", 1, True)],
)
def test_usersdata_unique_category_and_id_number(
    category: str, id_number: int, is_error: bool
):
    assert False


def test_usersdata_get_related_record():
    assert False


def test_usersdata_object_as_dict():
    assert False
