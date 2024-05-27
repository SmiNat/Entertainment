import os
from typing import Callable

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from entertainment.routers.utils import (
    check_country,
    check_date,
    check_if_author_or_admin,
    check_items_list,
    check_items_list_and_convert_to_a_string,
    check_language,
    convert_items_list_to_a_sorted_string,
    convert_list_to_unique_values,
    get_unique_row_data,
    validate_field,
)
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_movies import create_movie
from entertainment.tests.utils_users import create_db_user


def test_get_unique_row_data_with_path_argument(database_genres):
    test_path = os.environ.get("DEV_DATABASE_PATH")
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
        (["item1", "new_item", "Item7", "item1"], "Item7, item1, new_item"),
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
    assert "Invalid country name. Available country names:" in exc_info.value.detail


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
    assert "Invalid language name. Available languages:" in exc_info.value.detail


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
            "Invalid language name. Available languages",
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
            "Invalid country name. Available country names",
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
            ["A", "kk", "zzz", "A", "gdh", "Bbn", "A", "ZZZ"],
            False,
            None,
            ["A", "Bbn", "Gdh", "Kk", "Zzz"],
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
