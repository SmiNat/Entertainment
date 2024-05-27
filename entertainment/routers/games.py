import datetime
import logging
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from entertainment.database import get_db
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
    # review_overall = enumerate


@router.get("/get_choices", status_code=status.HTTP_200_OK)
async def get_choices(db: db_dependency, field: FieldChoices = Query()) -> list:
    results = get_unique_row_data(db, "games", field.value)
    return results
