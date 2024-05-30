import datetime
import logging
from enum import Enum
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import GamesReviewDetailed, GamesReviewOverall
from entertainment.exceptions import DatabaseIntegrityError
from entertainment.models import Games
from entertainment.routers.auth import get_current_user
from entertainment.utils import (
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
    game_type: list[str] | None
    price_eur: float | None = Field(default=None, ge=0)
    price_discounted_eur: float | None = Field(default=None, ge=0)
    review_overall: GamesReviewOverall | None
    review_detailed: GamesReviewDetailed | None
    reviews_positive: float | None = Field(default=None, ge=0, le=1)


class GameResponse(GameRequest):
    genres: str
    game_type: str
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


@router.get("/search", status_code=200)
async def search_games():
    pass


@router.post("/add", status_code=201, response_model=GameResponse)
async def add_game(
    user: user_dependency,
    db: db_dependency,
    new_game: GameRequest,
) -> Games:
    all_fields = new_game.model_dump()

    # Validate fields: genres and type and convert a list to a string
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
