import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path  # noqa
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import (
    EntertainmentCategory,
    MyRate,
    WishlistCategory,
)
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import CATEGORY_MODEL_MAP, UsersData  # noqa
from entertainment.routers.auth import get_current_user
from entertainment.utils import validate_rate

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/assess", tags=["assessment"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class AssessmentRequest(BaseModel):
    finished: bool = Field(default=False)
    wishlist: WishlistCategory | None = None
    watchlist: bool = Field(default=False)
    official_rate: str | int | None = None
    priv_rate: MyRate | None = None
    publ_comment: str | None = None
    priv_notes: str | None = None


class UserAssessment(AssessmentRequest):
    category: EntertainmentCategory
    id_number: int

    @field_validator("category", mode="before")
    def case_insensitive_category(cls, value):
        if isinstance(value, str):
            value = value.strip().capitalize()
        return value


class ResponseModel(UserAssessment):
    record_title: str


@router.post("/add", status_code=202, response_model=ResponseModel)
async def my_assessment(db: db_dependency, user: user_dependency, data: UserAssessment):
    assessment = UsersData(**data.model_dump(), created_by=user["username"])

    if data.official_rate:
        validate_rate(data.official_rate, data.category)

    db_related_record = assessment.get_related_record(db)
    if not db_related_record:
        raise RecordNotFoundException(
            extra_data=f"Searched record: {data.id_number} (id) in {data.category} category."
        )

    try:
        title = db_related_record.title
        assessment.db_record = title

        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    except AttributeError:
        raise HTTPException(404, f"'{data.category}' object has no attribute 'title'.")
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data=f"A record with id '{data.id_number}' has already been assessed."
        )

    response_data = data.model_dump()
    response_data.update({"record_title": title})

    return ResponseModel(**response_data)


@router.patch("/{category}/{id_number}", status_code=202, response_model=ResponseModel)
async def record_assessment(
    db: db_dependency,
    user: user_dependency,
    data: AssessmentRequest,
    category: str = Path(enum=EntertainmentCategory.list_of_values()),
    id_number: int = Path(),
):
    model = CATEGORY_MODEL_MAP.get(category.capitalize())
    print(">>>>>>>>>>>> 1", model, category)
    if not model:
        raise HTTPException(
            404, f"'{category.capitalize()}' category was not found in the database."
        )
    record = db.query(model).get(id_number)
    print(">>>>>>>>>>>> 2", record, id_number)
    if not record:
        raise RecordNotFoundException(
            extra_data=f"Searched record: id '{id_number}' in {category} category."
        )

    assessment = (
        db.query(UsersData)
        .filter(
            UsersData.category == category.capitalize(),
            UsersData.id_number == id_number,
        )
        .first()
    )
    print(">>>>>>>>>>>> 3", assessment)
    if not assessment:
        raise RecordNotFoundException(
            extra_data=f"Searched record: {id_number} (id) in {category} category."
        )

    for attr, value in data.model_dump().items():
        if value is not None:
            setattr(assessment, attr, value)

    db.commit()
    db.refresh(assessment)

    try:
        title = record.title
    except AttributeError:
        raise HTTPException(404, f"'{category}' object has no attribute 'title'.")

    response_data = data.model_dump()
    response_data.update({"record_title": title})

    return response_data
