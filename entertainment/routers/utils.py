import datetime
from typing import Callable

import pycountry
from fastapi import HTTPException, status


def check_date(date_value: str, format: str = "%Y-%m-%d") -> None:
    try:
        datetime.datetime.strptime(date_value, format).date()
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date type. Enter date in 'YYYY-MM-DD' format.",
        )


def check_genres_list(genres: list[str], accessible_genres: list[str]):
    if not genres or all(element is None for element in genres):
        return
    genres_list = [genre.strip().title() for genre in genres if genre]
    for genre in genres_list:
        if genre in [genre.title() for genre in accessible_genres]:
            continue
        else:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Invalid genre: check 'get movies genres' for list of accessible genres.",
            )
    genres_list.sort()
    # genres_string = ", ".join(genres_list)
    # return genres_string
    return genres_list


def convert_genres_list_to_a_string(genres: list) -> str:
    if not genres:
        return ""
    genres_list = genres
    genres_list.sort()
    genres_string = ", ".join(genres_list)
    return genres_string


def check_genres_list_and_convert_to_a_string(
    genres: list[str], accessible_genres: list[str]
):
    if not genres or all(element is None for element in genres):
        return
    genres_list = [genre.strip().title() for genre in genres if genre]
    for genre in genres_list:
        if genre in [genre.title() for genre in accessible_genres]:
            continue
        else:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Invalid genre: check 'get movies genres' for list of accessible genres.",
            )
    genres_list.sort()
    genres_string = ", ".join(genres_list)
    return genres_string


def check_country(country: str) -> str | None:
    """Verifies country name and return ISO alpha-2-code of a given country."""
    if not country:
        return
    try:
        result = pycountry.countries.lookup(country.strip())
        return dict(result)["alpha_2"]
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid country name. Available country names: %s"
            % [{country.alpha_2: country.name} for country in pycountry.countries],
        )


def check_language(language: str) -> str | None:
    """Verifies language in ISO language codes and returns a language name."""
    if not language:
        return
    try:
        result = pycountry.languages.lookup(language.strip())
        return dict(result)["name"]
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid language name. Available languages: %s"
            % [language.name for language in pycountry.languages],
        )


def validate_field(
    field_name: str, fields_to_update: dict, func: Callable, *args, **kwargs
):
    """
    Verifies if field value is valid before making changes in the database.
    Validation is made based on provided check function.
    """
    if field_name in fields_to_update.keys():
        field_value = func(fields_to_update[field_name], *args, **kwargs)
        if not field_value:
            del fields_to_update[field_name]
        else:
            fields_to_update[field_name] = field_value
    return fields_to_update


def convert_list_to_unique_values(
    values_to_check: list[str],
    nested_values_inside_strings: bool = True,
    sep: str = ",",
):
    """
    Converts a list of strings to a list of unique values.
    If the string values in the list represent a list itself, converts each string
    to the list based on the indicated separator and from these lists creates
    a unique list sorted by value.
    """
    if not nested_values_inside_strings:
        return sorted(set(value.title() for value in values_to_check))

    unique_values = set()
    for value in values_to_check:
        if value:
            if "," not in value:
                unique_values.add(value.title())
            else:
                values_list = value.split(sep)
                for element in values_list:
                    element = str(element).strip()
                    unique_values.add(element.title())
    return sorted(unique_values)
