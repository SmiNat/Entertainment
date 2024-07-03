import os
import sqlite3
from typing import Callable

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_movies import create_movie
from entertainment.tests.utils_users import create_db_user
from entertainment.utils import (
    check_country,
    check_date,
    check_if_author_or_admin,
    check_items_list,
    check_items_list_and_convert_to_a_string,
    check_language,
    convert_items_list_to_a_sorted_string,
    convert_list_to_unique_values,
    get_genre_by_subgenre,
    get_unique_row_data,
    smart_title,
    validate_field,
    validate_rate,
)


@pytest.mark.parametrize(
    "category, rate",
    [
        ("Books", 1),
        ("Games", "Mixed"),
        ("Movies", 6),
        ("Songs", None),
    ],
)
def test_validate_rate_ok(category: str, rate: str | int):
    assert validate_rate(rate, category) is None


@pytest.mark.parametrize(
    "category, rate, exp_result",
    [
        ("Songs", 1, "No official rate system provided for Songs category"),
        (
            "Invalid",
            3,
            "Invalid category. Accessable categories: ['Books', 'Games', 'Songs', 'Movies']",
        ),
        ("Books", 9, [1, 2, 3, 4, 5]),
        ("Books", "1", ""),
        ("Books", "Mixed", [1, 2, 3, 4, 5]),
        ("Games", 1, "['Very Negative', 'Negative"),
        ("Games", "1", "['Very Negative', 'Negative"),
        ("Movies", 11, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ("Movies", "8", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ("Movies", "Mixed", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
    ],
)
def test_validate_rate_400(category: str, rate: str | int, exp_result: str | list):
    if category == "Songs" or category == "Invalid":
        exp_response = exp_result
    else:
        exp_response = f"'{rate}' is not a valid official rate. Official rates for '{category}' category: {exp_result}"
    with pytest.raises(HTTPException) as exc_info:
        validate_rate(rate, category)
    assert exc_info.value.status_code == 400
    assert exp_response in exc_info.value.detail


def test_smart_title():
    example = "TV Movie, TV movie, RPG, Multi-player, fantasy, World War II"
    expected_result = "TV Movie, TV Movie, RPG, Multi-player, Fantasy, World War II"
    assert smart_title(example) == expected_result
    assert smart_title(example, "invalid") == expected_result


def test_smart_title_lower():
    example = "TV Movie, TV movie, RPG, Multi-player, fantasy, World War II"
    expected_result = "tv movie, tv movie, rpg, multi-player, fantasy, world war ii"
    assert smart_title(example, "lower") == expected_result


def test_get_unique_row_data_with_path_argument():
    test_path = os.path.join(
        "entertainment/tests/", os.environ.get("TEST_DATABASE_PATH")
    )

    # Creating database initial data
    conn = sqlite3.connect(test_path)

    # Drop the table if it exists
    drop_table = """DROP TABLE IF EXISTS test_table;"""
    conn.execute(drop_table)

    # Create a new table
    test_table = """
    CREATE TABLE test_table (
    id      INTEGER     PRIMARY KEY,
    title   VARCHAR,
    genres  TEXT
    );
    """
    conn.execute(test_table)

    # Fill the table with content
    content = """
    INSERT INTO test_table (title, genres)
    VALUES
        ("First test", "Classics, Drama, Fiction"),
        ("A new test", "Classics, Magic, Mythology"),
        ("Another test", "Classics, Fantasy, Fiction");
    """
    conn.execute(content)

    conn.commit()
    conn.close()

    # Testing function get_unique_row_data
    table_name = "test_table"
    expected_result = [
        "Classics",
        "Drama",
        "Fantasy",
        "Fiction",
        "Magic",
        "Mythology",
    ]
    assert expected_result == get_unique_row_data(test_path, table_name, "genres")


def test_get_unique_row_data_with_path_argument_with_subvalue():
    test_path = os.path.join(
        "entertainment/tests/", os.environ.get("TEST_DATABASE_PATH")
    )

    # Creating database initial data
    conn = sqlite3.connect(test_path)

    # Drop the table if it exists
    drop_table = """DROP TABLE IF EXISTS test_table;"""
    conn.execute(drop_table)

    # Create a new table
    test_table = """
    CREATE TABLE test_table (
    id          INTEGER     PRIMARY KEY,
    title       VARCHAR,
    genres      TEXT,
    sub_genres  TEXT
    );
    """
    conn.execute(test_table)

    # Fill the table with content
    content = """
    INSERT INTO test_table (title, genres, sub_genres)
    VALUES
        ("First test", "Fiction", "xyz"),
        ("A new test", "Mythology", "abc"),
        ("Another test", "Fiction", "xyz"),
        ("Some test", "Fiction", "aaa");
    """
    conn.execute(content)

    conn.commit()
    conn.close()

    # Testing function get_unique_row_data
    table_name = "test_table"
    expected_result = ["aaa", "xyz"]
    assert expected_result == get_unique_row_data(
        test_path, table_name, "genres", "sub_genres", "Fiction", "lower"
    )


def test_get_unique_row_data_with_session_argument():
    # Creatina a 'test_table' with 'title' and 'genres' columns
    new_table = """
    CREATE TABLE test_table (
    id      INTEGER     PRIMARY KEY,
    title   VARCHAR,
    genres  TEXT
    );
    """
    new_content = """
    INSERT INTO test_table (title, genres)
    VALUES
        ("First test", "Classics, Drama, Fiction"),
        ("A new test", "Classics, Magic, Mythology"),
        ("Another test", "Classics, Fantasy, Fiction");
    """

    # Using the same session for creating the table, inserting data, and testing
    with TestingSessionLocal() as session:
        # Creating table and inserting data
        session.execute(text(new_table))
        session.execute(text(new_content))
        session.commit()

        # Testing if get_unique_row_data will return expected result
        table_name = "test_table"
        expected_result = [
            "Classics",
            "Drama",
            "Fantasy",
            "Fiction",
            "Magic",
            "Mythology",
        ]
        result = get_unique_row_data(session, table_name, "genres")
        assert sorted(expected_result) == sorted(result)


def test_get_unique_row_data_with_session_argument_with_subcolumn_value():
    new_table = """
    CREATE TABLE test_table (
    id          INTEGER     PRIMARY KEY,
    title       VARCHAR,
    genres      TEXT,
    sub_genres  TEXT
    );
    """
    new_content = """
    INSERT INTO test_table (title, genres, sub_genres)
    VALUES
        ("First test", "Fiction", "xyz"),
        ("A new test", "Mythology", "abc"),
        ("Another test", "Fiction", "xyz"),
        ("Some test", "Fiction", "aaa");
    """

    # Using the same session for creating the table, inserting data, and testing
    with TestingSessionLocal() as session:
        # Creating table and inserting data
        session.execute(text(new_table))
        session.execute(text(new_content))
        session.commit()

        # Testing if get_unique_row_data will return expected result
        table_name = "test_table"
        expected_result = ["xyz", "aaa"]
        result = get_unique_row_data(
            session, table_name, "genres", "sub_genres", "Fiction", "lower"
        )
        assert sorted(expected_result) == sorted(result)


def test_get_genre_by_subgenre_with_session_argument():
    new_table = """
    CREATE TABLE test_table (
    id          INTEGER     PRIMARY KEY,
    title       VARCHAR,
    genres      TEXT,
    sub_genres  TEXT
    );
    """
    new_content = """
    INSERT INTO test_table (title, genres, sub_genres)
    VALUES
        ("First test", "Fiction", "xyz"),
        ("A new test", "Mythology", "abc"),
        ("Another test", "Fiction", "xyz"),
        ("Some test", "Fiction", "aaa");
    """

    # Using the same session for creating the table, inserting data, and testing
    with TestingSessionLocal() as session:
        # Creating table and inserting data
        session.execute(text(new_table))
        session.execute(text(new_content))
        session.commit()

        # Testing if get_genre_by_subgenre will return expected result
        table_name = "test_table"
        expected_result = ["Fiction"]
        result = get_genre_by_subgenre(
            session, table_name, "genres", "sub_genres", "xyz"
        )
        assert sorted(expected_result) == sorted(result)


def test_get_genre_by_subgenre_with_path_argument():
    test_path = os.path.join(
        "entertainment/tests/", os.environ.get("TEST_DATABASE_PATH")
    )

    # Creating database initial data
    conn = sqlite3.connect(test_path)

    # Drop the table if it exists
    drop_table = """DROP TABLE IF EXISTS test_table;"""
    conn.execute(drop_table)

    # Create a new table
    test_table = """
    CREATE TABLE test_table (
    id          INTEGER     PRIMARY KEY,
    title       VARCHAR,
    genres      TEXT,
    sub_genres  TEXT
    );
    """
    conn.execute(test_table)

    # Fill the table with content
    content = """
    INSERT INTO test_table (title, genres, sub_genres)
    VALUES
        ("First test", "Fiction", "xyz"),
        ("A new test", "Mythology", "abc"),
        ("Another test", "Fiction", "xyz"),
        ("Some test", "Fiction", "aaa");
    """
    conn.execute(content)

    conn.commit()
    conn.close()

    # Testing function get_genre_by_subgenre
    table_name = "test_table"
    expected_result = ["Mythology"]
    assert expected_result == get_genre_by_subgenre(
        test_path, table_name, "genres", "sub_genres", "abc"
    )


@pytest.mark.parametrize(
    "username, role, created_by, is_exception_risen",
    [
        ("test_user", "user", "test_user", False),
        ("test_user", "admin", "other_user", False),
        ("test_user", "user", "other_user", True),
    ],
)
def test_check_if_author_or_admin(
    username: str, role: str, created_by: str, is_exception_risen: bool
):
    user = create_db_user(username=username, role=role)
    record = create_movie(created_by=created_by)
    if is_exception_risen:
        with pytest.raises(HTTPException) as exc_info:
            check_if_author_or_admin(user, record)
        assert exc_info.value.status_code == 403
        assert (
            "Only a user with the 'admin' role or the author of the database "
            "record can change or delete the record from the database."
            in exc_info.value.detail
        )
    else:
        assert check_if_author_or_admin(user, record) is None


def test_check_date():
    invalid_date = "20-10-2020"
    # Example test case where date is invalid
    check_date("2020-10-20")

    # Example test case where date is invalid
    with pytest.raises(HTTPException) as exc_info:
        check_date(invalid_date)
    assert (
        "Invalid date type. Enter date in 'YYYY-MM-DD' format." in exc_info.value.detail
    )
    assert exc_info.value.status_code == 422


@pytest.mark.parametrize(
    "example_list, is_valid, expected_result",
    [
        (["war", "romance", "action", "war"], True, ["Action", "Romance", "War"]),
        ([None, None], True, None),
        (
            ["war", "crazy", "invalid"],
            False,
            "Invalid genre: check 'get genres' for list of accessible genres",
        ),
    ],
)
def test_check_items_list(
    example_list: list, is_valid: bool, expected_result: list | str | None
):
    accessible_items = [
        "Action",
        "Comedy",
        "Crime",
        "Horror",
        "History",
        "Romance",
        "War",
    ]
    if is_valid:
        result = check_items_list(example_list, accessible_items)
        assert result == expected_result
    else:
        with pytest.raises(HTTPException) as exc_info:
            check_items_list(example_list, accessible_items)
        assert exc_info.value.status_code == 422
        assert expected_result in exc_info.value.detail


@pytest.mark.parametrize(
    "example_list, expected_result",
    [
        (
            ["item1", "new_item", "Item7", "item1", "new item"],
            "Item1, Item7, New Item, New_item",
        ),
        ([None, None, None], None),
        (None, None),
    ],
)
def test_convert_items_list_to_a_sorted_string(
    example_list: list | None, expected_result: str | None
):
    result = convert_items_list_to_a_sorted_string(example_list)
    assert expected_result == result


def test_check_items_list_and_convert_to_a_string():
    accessible_items = [
        "Action",
        "Comedy",
        "Crime",
        "Horror",
        "History",
        "Romance",
        "War",
    ]
    # Example test case where items are valid
    response = check_items_list_and_convert_to_a_string(
        ["action", "war", "comedy"], accessible_items
    )
    assert response == "Action, Comedy, War"

    # Example test case where items are invalid
    with pytest.raises(HTTPException) as exc_info:
        check_items_list_and_convert_to_a_string(
            ["romance", "history", "statistics"], accessible_items
        )
    assert exc_info.value.status_code == 422
    assert (
        "Invalid genre: check 'get genres' for list of accessible genres"
        in exc_info.value.detail
    )

    # Example test case with list of empty records
    response = check_items_list_and_convert_to_a_string([None, None], accessible_items)
    assert response is None


@pytest.mark.parametrize(
    "valid_data", [("pl"), ("pol"), ("Poland"), ("poland"), ("   poland")]
)
def test_check_country_with_valid_data(valid_data: str):
    response = check_country(valid_data)
    assert response == "PL"


def test_check_country_with_invalid_data():
    with pytest.raises(HTTPException) as exc_info:
        check_country("invalid_country")
    assert exc_info.value.status_code == 422
    assert (
        "Invalid country name: 'invalid_country'. Available country names:"
        in exc_info.value.detail
    )


def test_check_country_with_empty_data():
    response = check_country(None)
    assert response is None


@pytest.mark.parametrize(
    "valid_data", [("pl"), ("pol"), ("polish"), ("Polish"), ("   polish")]
)
def test_check_language_with_valid_data(valid_data: str):
    response = check_language(valid_data)
    assert response == "Polish"


def test_check_language_with_invalid_data():
    with pytest.raises(HTTPException) as exc_info:
        check_language("polnish")
    assert exc_info.value.status_code == 422
    assert (
        "Invalid language name: 'polnish'. Available languages:"
        in exc_info.value.detail
    )


def test_check_language_with_empty_data():
    response = check_language(None)
    assert response is None


@pytest.mark.parametrize(
    "field_name, fields_to_update, func_name, exp_result",
    [
        (
            "genres",
            {"genres": [None, None], "score": 6.6},
            check_items_list_and_convert_to_a_string,
            {"score": 6.6},
        ),
        (
            "genres",
            {"genres": ["Action", "War"], "score": 6.6},
            check_items_list_and_convert_to_a_string,
            {"genres": "Action, War", "score": 6.6},
        ),
        (
            "genres",
            {"genres": ["cinema", "incorrect"], "score": 6.6},
            check_items_list_and_convert_to_a_string,
            "Invalid genre: check 'get genres' for list of accessible genres",
        ),
        (
            "orig_lang",
            {"orig_lang": "polish", "score": 6.6},
            check_language,
            {"orig_lang": "Polish", "score": 6.6},
        ),
        (
            "orig_lang",
            {"orig_lang": "pl", "score": 6.6},
            check_language,
            {"orig_lang": "Polish", "score": 6.6},
        ),
        (
            "orig_lang",
            {"orig_lang": "invalid", "score": 6.6},
            check_language,
            "Invalid language name: 'invalid'. Available languages",
        ),
        (
            "country",
            {"country": "poland", "score": 6.6},
            check_country,
            {"country": "PL", "score": 6.6},
        ),
        (
            "country",
            {"country": "invalid", "score": 6.6},
            check_country,
            "Invalid country name: 'invalid'. Available country names",
        ),
    ],
)
def test_validate_field(
    field_name: str,
    fields_to_update: dict,
    func_name: Callable,
    exp_result: dict | str,
):
    accessible_genres = ["Action", "Comedy", "War"]

    if isinstance(exp_result, str):
        with pytest.raises(HTTPException) as exc_info:
            if field_name == "genres":
                validate_field(
                    field_name, fields_to_update, func_name, accessible_genres
                )
            else:
                validate_field(field_name, fields_to_update, func_name)
        assert exc_info.value.status_code == 422
        assert exp_result in exc_info.value.detail
    else:
        if field_name == "genres":
            result = validate_field(
                field_name, fields_to_update, func_name, accessible_genres
            )
        else:
            result = validate_field(field_name, fields_to_update, func_name)
        assert result == exp_result


@pytest.mark.parametrize(
    "example_list, is_value_nested, separator, expected_result",
    [
        (
            ["A", "kk", "a", "zzz", "gdh", "Bbn", "A", "ZZZ"],
            False,
            None,
            ["A", "Bbn", "Gdh", "Kk", "ZZZ", "Zzz"],
        ),
        (
            ["Aa, Bb", "kk, Zz", "bB, Ww, aa", "X"],
            True,
            ",",
            ["Aa", "Bb", "Kk", "Ww", "X", "Zz"],
        ),
    ],
)
def test_convert_list_to_unique_values(
    example_list: list,
    is_value_nested: bool,
    separator: str | None,
    expected_result: list,
):
    result = convert_list_to_unique_values(example_list, is_value_nested, separator)
    assert result == expected_result
