import datetime
import sqlite3
from typing import Callable

import pycountry
from fastapi import HTTPException, status

from entertainment.models import Books, Games, Movies, Songs, Users


def get_unique_genres(db_path, table_name: str):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute the query to get all genres
    cursor.execute(f"SELECT genres FROM {table_name}")

    # Fetch all results
    genres_data = cursor.fetchall()

    # Close the connection
    conn.close()

    # Process the fetched genres to get unique values
    all_genres = set()
    for row in genres_data:
        genres = row[0].split(", ")
        all_genres.update(genres)

    # Extract unique values from each genre string in genres list
    genres = convert_list_to_unique_values(list(all_genres))
    return genres


def check_if_author_or_admin(
    user: Users | dict, record: Books | Games | Movies | Songs
):
    """Validates if user is either the author of a given database record or
    if user has 'admin' status. Otherwise raises HTTP Exception."""
    role = user["role"] if isinstance(user, dict) else user.role
    username = user["username"] if isinstance(user, dict) else user.username
    if not (role == "admin" or username == record.created_by):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only a user with the 'admin' role or the author of the "
            "database record can change or delete the record from the database.",
        )


def check_date(date_value: str, format: str = "%Y-%m-%d") -> None:
    """Validates if date field is presented in correct format."""
    try:
        datetime.datetime.strptime(date_value, format).date()
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date type. Enter date in 'YYYY-MM-DD' format.",
        )


def check_items_list(
    items: list[str],
    accessible_items: list[str],
    status_code: int = 422,
    error_message: str = "Invalid genre: check 'get genres' for list of accessible genres.",
) -> list:
    """Validates if all items are acceptable given accessible items list.
    Returns unique, sorted list of items."""
    if not items or all(element is None for element in items):
        return

    items_list = [item.strip().title() for item in items if item]
    accessible_items = [item.strip().title() for item in accessible_items]

    items_set = set()
    for item in items_list:
        if item in accessible_items:
            items_set.add(item)
        else:
            raise HTTPException(status_code=status_code, detail=error_message)

    items_list = list(items_set)
    items_list.sort()
    return items_list


def convert_items_list_to_a_sorted_string(items: list[str]) -> str | None:
    """Converts a list of items into a string of unique sorted items."""
    if not items:
        return None
    items = list(set(items))
    items.sort()
    items_string = ", ".join(items)
    return items_string


def check_items_list_and_convert_to_a_string(
    items: list[str], accessible_items: list[str]
) -> str | None:
    """Validates if all items are acceptable given accessible items list.
    Returns unique, sorted list of items converted into a string."""
    items_list = check_items_list(items, accessible_items)
    items_string = ", ".join(items_list) if items_list else None
    return items_string


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
    If the string values in the list represents a list itself, converts each string
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
