import datetime
import logging
from enum import Enum
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, extract, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import GamesReviewDetailed, GamesReviewOverall
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import Games
from entertainment.routers.auth import get_current_user
from entertainment.utils import (
    check_if_author_or_admin,
    check_items_list,
    convert_items_list_to_a_sorted_string,
    get_unique_row_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["games"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class FieldChoices(str, Enum):
    overall_review = "review_overall"
    detailed_review = "review_detailed"
    genres = "genres"
    game_type = "type"


class GameRequest(BaseModel):
    title: str
    premiere: datetime.date = Field(description="YYYY-MM-DD format.")
    developer: str
    publisher: str | None = Field(default=None, examples=[None])
    genres: list[str] = Field()
    game_type: list[str | None] | None = Field(default=[None], examples=[[None]])
    price_eur: float | None = Field(default=None, ge=0)
    price_discounted_eur: float | None = Field(default=None, ge=0)
    review_overall: GamesReviewOverall | None = None
    review_detailed: GamesReviewDetailed | None = None
    reviews_positive: float | None = Field(default=None, ge=0, le=1)
    reviews_number: int | None = Field(default=None, ge=0)


class UpdateGameRequest(GameRequest):
    title: str | None = Field(default=None, examples=[None])
    premiere: datetime.date | None = Field(default=None, examples=[None])
    developer: str | None = Field(default=None, examples=[None])
    genres: list[str | None] | None = Field(default=[None], examples=[[None, None]])

    class DictConfig:
        from_attributes = True


class GameResponse(GameRequest):
    genres: str
    game_type: str | None
    review_detailed: str | None
    review_overall: str | None
    id: int
    created_by: str | None
    updated_by: str | None

    class DictConfig:
        from_attributes = True


class ResponseModel(BaseModel):
    number_of_games: int
    page: str
    games: list[GameResponse]


@router.get("/get_choices", status_code=status.HTTP_200_OK)
async def get_choices(db: db_dependency, field: FieldChoices = Query()) -> list:
    results = get_unique_row_data(db, "games", field.value)
    return results


@router.get(
    "/all",
    status_code=200,
    response_model=ResponseModel,
    response_model_exclude_none=True,
)
async def get_all_games(
    db: db_dependency,
    page_size: int = Query(
        default=10, ge=1, le=100, description="Number of records per page."
    ),
    page_number: int = Query(1, gt=0),
):
    games = db.query(Games)

    results = games.offset((page_number - 1) * page_size).limit(page_size).all()
    if not results:
        raise HTTPException(404, "Games not found.")

    return {
        "number_of_games": games.count(),
        "page": f"{page_number} of {ceil(games.count()/page_size)}",
        "games": results,
    }


@router.get(
    "/search",
    status_code=200,
    response_model=ResponseModel,
    response_model_exclude_none=True,
)
async def search_games(
    db: db_dependency,
    title: str | None = None,
    premiere_year: int | None = None,
    developer: str | None = None,
    publisher: str | None = None,
    genres: str | None = None,
    game_type: str | None = None,
    review_overall: str | None = Query(
        default=None, enum=["Negative", "Mixed", "Positive"]
    ),
    review_detailed: str | None = Query(
        default=None, enum=GamesReviewDetailed.list_of_values()
    ),
    reviews_number: int | None = Query(
        default=None, description="Minimal number of reviews."
    ),
    reviews_positive: float | None = Query(
        default=None, ge=0, le=1, description="Percentage of positive reviews."
    ),
    exclude_empty_data: bool = Query(
        default=False,
        description="To exclude from search the records with empty reviews_number "
        "or empty reviews_positive fields.",
    ),
    order_by: str | None = Query(
        default=None,
        enum=["title", "premiere", "price_eur", "reviews_number", "reviews_positive"],
    ),
    order_type: str = Query("ascending", enum=["ascending", "descending"]),
    page_number: int = Query(1, ge=1),
):
    params = locals().copy()
    params_with_values = [
        x
        for x in params
        if params[x] is not None
        and x not in ["db", "order_by", "order_type", "page_number"]
    ]

    icontains_fields = [
        "title",
        "developer",
        "publisher",
        "genres",
        "game_type",
        "review_overall",
        "review_detailed",
    ]
    gte_fields = ["reviews_number", "reviews_positive"]

    games = db.query(Games)

    for attr in params_with_values:
        if attr in icontains_fields:
            games = games.filter(getattr(Games, attr).icontains(params[attr].strip()))
        if attr in gte_fields:
            games = (
                games.filter(getattr(Games, attr) >= params[attr])
                if exclude_empty_data
                else games.filter(
                    or_(
                        getattr(Games, attr) >= params[attr],
                        getattr(Games, attr).is_(None),
                    )
                )
            )

    if premiere_year:
        games = games.filter(extract("year", Games.premiere).is_(premiere_year))

    if order_by:
        games = (
            games.order_by(desc(order_by))
            if order_type == "descending"
            else games.order_by(order_by)
        )

    results = games.offset((page_number - 1) * 10).limit(10).all()
    logger.debug("Database hits (search games): %s." % len(games.all()))

    if not results:
        raise HTTPException(404, "Games not found.")

    return {
        "number_of_games": games.count(),
        "page": f"{page_number} of {ceil(games.count()/10)}",
        "games": results,
    }


@router.post("/add", status_code=201, response_model=GameResponse)
async def add_game(
    user: user_dependency,
    db: db_dependency,
    new_game: GameRequest,
) -> Games:
    all_fields = new_game.model_dump()

    # Validate fields: genres and game_type and convert a list to a string
    fields_to_validate = ["genres", "game_type"]
    for field in fields_to_validate:
        accessible_options = get_unique_row_data(db, "games", field)
        check_items_list(
            all_fields[field],
            accessible_options,
            error_message=f"Invalid {field}: check 'get choices' for list of accessible {field}.",
        )
        result = convert_items_list_to_a_sorted_string(all_fields[field])
        all_fields[field] = result

    game = Games(**all_fields, created_by=user["username"])

    try:
        db.add(game)
        db.commit()
        db.refresh(game)
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data="A game with that title, premiere date and developer already exists in the database."
        )

    logger.debug(
        "Game: '%s' was successfully added to database by the '%s' user."
        % (game.title, user["username"])
    )
    return game


@router.patch("/{title}/{premiere}/{developer}", status_code=status.HTTP_200_OK)
async def update_game(
    db: db_dependency,
    user: user_dependency,
    game_update: UpdateGameRequest,
    title: str,
    developer: str,
    premiere: datetime.date = Path(description="Use YYYY-MM-DD, eg. 2024-07-22."),
):
    logger.debug("Game to update: '%s' (%s) by %s." % (title, premiere, developer))

    game = (
        db.query(Games)
        .filter(
            func.lower(Games.title) == title.strip().casefold(),
            func.lower(Games.developer) == developer.strip().casefold(),
            Games.premiere == premiere,
        )
        .first()
    )
    if not game:
        raise RecordNotFoundException(
            extra_data=f"Searched game: '{title}' ({premiere}) by {developer}."
        )

    # Verify if user is authorized to update a game
    check_if_author_or_admin(user, game)

    # Get all fields to update and check if genres and game_type are not an empty list
    fields_to_validate = game_update.model_dump(exclude_unset=True, exclude_none=True)
    fields_to_update = fields_to_validate.copy()

    for field, value in fields_to_validate.items():
        if field in ["genres", "game_type"] and all(x is None for x in value):
            del fields_to_update[field]
    if not fields_to_update:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="No data input provided."
        )
    logger.debug("Fields to update: %s" % fields_to_update)

    # Update fields
    for field, value in fields_to_update.items():
        logger.debug("Updating: field: %s, value: %s" % (field, value))
        if field in ["genres", "game_type"]:
            # Validate fields: genres and game_type and convert a list to a string
            accessible_options = get_unique_row_data(db, "games", field)
            check_items_list(
                value,
                accessible_options,
                error_message=f"Invalid {field}: check 'get choices' for list of accessible {field}.",
            )
            setattr(game, field, convert_items_list_to_a_sorted_string(value))
        else:
            setattr(game, field, value)
    game.updated_by = user["username"]

    # Insert changes into the database
    try:
        db.commit()
        db.refresh(game)
    except IntegrityError as e:
        raise DatabaseIntegrityError(detail=str(e.orig))

    logger.debug(
        "Game: '%s' was successfully updated by the '%s' user."
        % (game.title, user["username"])
    )
    return game


@router.delete(
    "/{title}/{premiere}/{developer}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_game(
    db: db_dependency,
    user: user_dependency,
    title: str = "",
    premiere: datetime.date = Path(description="Use YYYY-MM-DD, eg. 2024-07-22."),
    developer: str = "",
):
    logger.debug("Game to delete: '%s' (%s) by %s." % (title, premiere, developer))

    game = (
        db.query(Games)
        .filter(
            func.lower(Games.title) == title.strip().lower(),
            func.lower(Games.developer) == developer.strip().lower(),
            Games.premiere == premiere,
        )
        .first()
    )
    if not game:
        raise RecordNotFoundException(
            extra_data=f"Searched game: {title} ({premiere}) by {developer}."
        )

    # Verify if user is authorized to delete a game
    check_if_author_or_admin(user, game)

    db.delete(game)
    db.commit()

    logger.debug(
        "Game '%s' (%s) by %s was successfully deleted by the '%s' user."
        % (title, premiere, developer, user["username"])
    )
