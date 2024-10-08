import datetime
import sqlite3
from typing import Callable

import pycountry
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from entertainment.enums import GamesReviewDetailed
from entertainment.models import Books, Games, Movies, Songs, Users, UsersData

RATES_MODEL_MAP = {
    "Books": [1, 2, 3, 4, 5],
    "Games": GamesReviewDetailed.list_of_values(),
    "Songs": None,
    "Movies": [x for x in range(1, 11)],
}


def validate_rate(rate: str | int, category: str):
    if category not in RATES_MODEL_MAP.keys():
        raise HTTPException(
            400,
            f"Invalid category. Accessable categories: {list(RATES_MODEL_MAP.keys())}.",
        )
    if category == "Songs" and RATES_MODEL_MAP["Songs"] is None:
        if rate is not None:
            raise HTTPException(
                400, "No official rate system provided for Songs category."
            )
    if rate and rate not in RATES_MODEL_MAP[category]:
        raise HTTPException(
            400,
            f"'{rate}' is not a valid official rate. Official rates for '{category}' "
            f"category: {RATES_MODEL_MAP[category]}.",
        )


def smart_title(text: str, case_type: str | None = None):
    if case_type in ["upper", "lower", "capitalize", "title"]:
        return " ".join(getattr(word, case_type)() for word in text.split())
    return " ".join(
        word if word.isupper() else word.capitalize() for word in text.split()
    )


def get_unique_row_data(
    db_path_or_session: str | Session,
    table_name: str,
    main_column_name: str,
    sub_column_name: str | None = None,
    main_col_value: str | None = None,
    case_type: str | None = None,
):
    """
    Extracts all unique values from a given database table, returns the list of
    unique column values.
    If values are stored in rows as a string separated with commas instead of
    a list of strings, converts values as a string into a list before returning
    unique values.

    If both sub_column_name and main_col_value are provided, extracts unique values
    from sub_column_name where the value of main_column_name (selected row) equals
    to main_col_value.

    Parameters:
        db_path_or_session (str | Session): Database path or SQLAlchemy Session object.
        table_name (str): The name of the table in the database.
        main_column_name (str): The name of the main column to query.
        sub_column_name (str | None): The name of the sub-column to get unique values from, if specified.
        main_col_value (str | None): The value of the main column to filter by, if specified.
        case_type (str | None): Letter size: "upper", "lower", "capitalize", "title".

    Returns:
        List: A list of unique values from the specified column(s).
    """
    all_rows_data = []  # Initialize all_rows_data with an empty list

    if isinstance(db_path_or_session, str):
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path_or_session)
        cursor = conn.cursor()

        # Execute the query to get all row values
        if sub_column_name and main_col_value:
            cursor.execute(
                f"SELECT DISTINCT {sub_column_name} FROM {table_name} WHERE {main_column_name} = ?",
                (main_col_value,),
            )
        else:
            cursor.execute(f"SELECT DISTINCT {main_column_name} FROM {table_name}")

        # Fetch all results
        all_rows_data = cursor.fetchall()

        # Close the connection
        conn.close()

    elif isinstance(db_path_or_session, Session):
        # Use the SQLAlchemy session to execute the query
        if sub_column_name and main_col_value:
            query = text(
                f"SELECT DISTINCT {sub_column_name} FROM {table_name} WHERE {main_column_name} = :main_col_value"
            )
            result = db_path_or_session.execute(
                query, {"main_col_value": main_col_value}
            )
        else:
            query = text(f"SELECT DISTINCT {main_column_name} FROM {table_name}")
            result = db_path_or_session.execute(query)
        all_rows_data = result.fetchall()

    # Process the fetched values to get unique values
    all_values = set()
    for row in all_rows_data:
        if isinstance(row[0], list):
            all_values.update(row[0])
        elif isinstance(row[0], str):
            values = row[0].split(", ")
            all_values.update(values)

    # Extract unique values from each value string in values list
    values = convert_list_to_unique_values(
        list(all_values),
        case_type=case_type,
    )
    return values


def get_genre_by_subgenre(
    db_path_or_session: str | Session,
    table_name: str,
    genre_column_name: str,
    subgenre_column_name: str,
    subgenre_value: str,
):
    """Extracts the genre name from a given database table based on a subgenre value.

    Parameters:
        db_path_or_session (str | Session): Database path or SQLAlchemy Session object.
        table_name (str): The name of the table in the database.
        genre_column_name (str): The name of the genre column to query.
        subgenre_column_name (str): The name of the subgenre column to filter by.
        subgenre_value (str): The value of the subgenre to search for.

    Returns:
        List: A list of genres matching the subgenre value.
    """
    all_rows_data = []  # Initialize all_rows_data with an empty list

    if isinstance(db_path_or_session, str):
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path_or_session)
        cursor = conn.cursor()

        # Execute the query to get the genre based on the subgenre
        cursor.execute(
            f"SELECT DISTINCT {genre_column_name} FROM {table_name} WHERE {subgenre_column_name} = ?",
            (subgenre_value,),
        )

        # Fetch all results
        all_rows_data = cursor.fetchall()

        # Close the connection
        conn.close()

    elif isinstance(db_path_or_session, Session):
        # Use the SQLAlchemy session to execute the query
        query = text(
            f"SELECT DISTINCT {genre_column_name} FROM {table_name} WHERE {subgenre_column_name} = :subgenre_value"
        )
        result = db_path_or_session.execute(query, {"subgenre_value": subgenre_value})
        all_rows_data = result.fetchall()

    # Extract the genre names from the fetched data
    genres = [row[0] for row in all_rows_data]

    return genres[0]


def check_if_author_or_admin(
    user: Users | dict, record: Books | Games | Movies | Songs | UsersData
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


def check_date(
    date_value: str,
    format: str = "%Y-%m-%d",
    error_message: str = "Invalid date type. Enter date in 'YYYY-MM-DD' format.",
) -> None:
    """Validates if date field is presented in correct format."""
    try:
        datetime.datetime.strptime(date_value, format).date()
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_message,
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


def convert_items_list_to_a_sorted_string(
    items: list[str], case_type: str | None = None
) -> str | None:
    """Converts a list of items into a string of unique sorted items."""
    if not items:
        return None
    items = list(set(smart_title(item.strip(), case_type) for item in items if item))
    if items == [None] or items == []:
        return None
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
            detail="Invalid country name: '%s'. Available country names: %s"
            % (
                country,
                [{country.alpha_2: country.name} for country in pycountry.countries],
            ),
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
            detail="Invalid language name: '%s'. Available languages: %s"
            % (language, [language.name for language in pycountry.languages]),
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
    case_type: str | None = None,
):
    """
    Converts a list of strings to a list of unique values.
    If the string values in the list represents a list itself, converts each string
    to the list based on the indicated separator and from these lists creates
    a unique list sorted by value.
    """
    if not nested_values_inside_strings:
        return sorted(set(smart_title(value, case_type) for value in values_to_check))

    unique_values = set()
    for value in values_to_check:
        if value:
            if "," not in value:
                unique_values.add(smart_title(value, case_type))
            else:
                values_list = value.split(sep)
                for element in values_list:
                    element = str(element).strip()
                    unique_values.add(smart_title(element, case_type=case_type))
    return sorted(unique_values)
