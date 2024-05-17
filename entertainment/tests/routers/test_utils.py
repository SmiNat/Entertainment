from typing import Callable

import pytest
from fastapi import HTTPException

from entertainment.routers.utils import (
    check_country,
    check_date,
    check_genres_list_and_convert_to_a_string,
    check_language,
    convert_list_to_unique_values,
    validate_field,
)


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


def test_check_genres_list_and_convert_to_a_string():
    accessible_movie_genres = [
        "Action",
        "Comedy",
        "Crime",
        "Horror",
        "History",
        "Romance",
        "War",
    ]
    # Example test case where genres are valid
    response = check_genres_list_and_convert_to_a_string(
        ["action", "war", "comedy"], accessible_movie_genres
    )
    assert response == "Action, Comedy, War"

    # Example test case where genres are invalid
    with pytest.raises(HTTPException) as exc_info:
        check_genres_list_and_convert_to_a_string(
            ["romance", "history", "statistics"], accessible_movie_genres
        )
    assert exc_info.value.status_code == 422
    assert (
        "Invalid genre: check 'get movies genres' for list of accessible genres"
        in exc_info.value.detail
    )

    # Example test case with list of empty records
    response = check_genres_list_and_convert_to_a_string(
        [None, None], accessible_movie_genres
    )
    assert response is None


@pytest.mark.parametrize(
    "valid_data", [("pl"), ("pol"), ("Poland"), ("poland"), ("   poland")]
)
def test_check_country_with_valid_data(valid_data: str):
    print(valid_data)
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
    print(valid_data)
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
            check_genres_list_and_convert_to_a_string,
            {"score": 6.6},
        ),
        (
            "genres",
            {"genres": ["Action", "War"], "score": 6.6},
            check_genres_list_and_convert_to_a_string,
            {"genres": "Action, War", "score": 6.6},
        ),
        (
            "genres",
            {"genres": ["cinema", "incorrect"], "score": 6.6},
            check_genres_list_and_convert_to_a_string,
            "Invalid genre: check 'get movies genres' for list of accessible genres",
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
