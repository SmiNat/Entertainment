import datetime
import logging
from enum import Enum
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import GamesReviewDetailed, GamesReviewOverall
from entertainment.models import Games
from entertainment.routers.auth import get_current_user
from entertainment.routers.utils import get_unique_row_data

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
    type: list[str]
    price_eur: float | None = Field(default=None)
    price_discounted_eur: float | None = Field(default=None)
    review_detailed: GamesReviewDetailed
    review_overall: GamesReviewOverall
    reviews_positive: float | None = Field(default=None, ge=0, le=1)


class GameResponse(GameRequest):
    genres: str
    type: str
    review_detailed: str
    review_overall: str
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
