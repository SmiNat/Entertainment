import logging
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from entertainment.database import get_db
from entertainment.enums import (
    EntertainmentCategory,
    MyRate,
    WishlistCategory,
)
from entertainment.exceptions import DatabaseIntegrityError, RecordNotFoundException
from entertainment.models import CATEGORY_MODEL_MAP, UsersData
from entertainment.routers.auth import get_current_user
from entertainment.utils import check_if_author_or_admin, validate_rate

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/assess", tags=["assessment"])

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class AssessmentRequest(BaseModel):
    finished: bool = Field(default=False)
    wishlist: WishlistCategory | None = None
    watchlist: bool = Field(default=False)
    official_rate: str | int | None = Field(default=None, examples=[None])
    priv_rate: MyRate | None = Field(default=None, examples=[None])
    publ_comment: str | None = Field(default=None, examples=[None])
    priv_notes: str | None = Field(default=None, examples=[None])


class UserAssessment(AssessmentRequest):
    category: EntertainmentCategory
    id_number: int

    @field_validator("category", mode="before")
    def case_insensitive_category(cls, value):
        if isinstance(value, str):
            value = value.strip().capitalize()
        return value


class ResponseModel(UserAssessment):
    db_record: str
    id: int


class SearchResponseModel(BaseModel):
    number_of_records: int
    page: str
    records: list[ResponseModel]


@router.get(
    "/search",
    status_code=200,
    response_model=SearchResponseModel,
    response_model_exclude_none=True,
)
async def search_records(
    db: db_dependency,
    user: user_dependency,
    category: str | None = Query(
        default=None, enum=EntertainmentCategory.list_of_values()
    ),
    title: str | None = Query(default=None),
    wishlist: str | None = Query(default=None, enum=WishlistCategory.list_of_values()),
    watchlist: bool | None = Query(default=None, enum=[True, False]),
    finished: bool | None = Query(default=None, enum=[True, False]),
    priv_rate: str | None = Query(default=None, enum=MyRate.list_of_values()),
    page_number: int = Query(default=1, ge=1),
):
    params = locals().copy()
    params_with_values = [
        x
        for x in params
        if params[x] is not None and x not in ["db", "user", "page_number"]
    ]

    icontains_fields = ["title", "wishlist", "priv_rate"]

    records = db.query(UsersData).filter(UsersData.created_by == user["username"])
    if not records.all():
        raise HTTPException(
            404, "User has not yet assessed any of the database records."
        )

    for attr in params_with_values:
        if attr == "category":
            records = records.filter(UsersData.category == params[attr])
        if attr in icontains_fields:
            records = records.filter(
                getattr(UsersData, attr).icontains(params[attr].strip())
            )
        if attr == "watchlist" or attr == "finished":
            records = records.filter(getattr(UsersData, attr).is_(params[attr]))

    results = records.offset((page_number - 1) * 10).limit(10).all()
    if not results:
        raise HTTPException(404, "Records not found.")

    return {
        "number_of_records": records.count(),
        "page": f"{page_number} of {ceil(records.count()/10)}",
        "records": results,
    }


@router.post("/add", status_code=200, response_model=ResponseModel)
async def add_assessment(
    db: db_dependency, user: user_dependency, data: UserAssessment
):
    assessment = UsersData(**data.model_dump(), created_by=user["username"])

    if data.official_rate:
        try:
            validate_rate(int(data.official_rate), data.category)
        except ValueError:
            validate_rate(data.official_rate, data.category)

    try:
        db_related_record = assessment.get_related_record(db)
    except OperationalError:
        raise HTTPException(404, f"'{data.category}' has no attribute 'title'.")
    if not db_related_record:
        raise RecordNotFoundException(
            extra_data=f"Searched record: id '{data.id_number}' in {data.category} category."
        )

    try:
        title = db_related_record.title
        assessment.db_record = title

        db.add(assessment)
        db.commit()
        db.refresh(assessment)

    except (AttributeError, OperationalError):
        raise HTTPException(404, f"'{data.category}' has no attribute 'title'.")
    except IntegrityError:
        raise DatabaseIntegrityError(
            extra_data=f"A record with id '{data.id_number}' from {data.category} category has already been assessed."
        )

    logger.debug(
        "Added UsersData record: '%s' from %s category (title: %s) by %s."
        % (data.id_number, data.category, title, user["username"])
    )

    return assessment


@router.patch(
    "/update/{category}/{id_number}", status_code=200, response_model=ResponseModel
)
async def update_assessment(
    db: db_dependency,
    user: user_dependency,
    data: AssessmentRequest,
    category: str = Path(enum=EntertainmentCategory.list_of_values()),
    id_number: int = Path(),
):
    logger.debug(
        "UsersData record to update: id_number '%s' (%s category) created by %s."
        % (id_number, category, user["username"])
    )

    model = CATEGORY_MODEL_MAP.get(category.capitalize())
    if not model:
        raise HTTPException(
            404, f"'{category.capitalize()}' category was not found in the database."
        )
    record = db.get(model, id_number)
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
    if not assessment:
        raise RecordNotFoundException(
            extra_data=f"UsersData has no record of id_number '{id_number}' from {category} category."
        )

    # Verify if user is authorized to update a users_data
    check_if_author_or_admin(user, assessment)

    if data.official_rate:
        try:
            validate_rate(int(data.official_rate), category)
        except ValueError:
            validate_rate(data.official_rate, category)

    for attr, value in data.model_dump().items():
        if value is not None:
            setattr(assessment, attr, value)

    db.commit()
    db.refresh(assessment)

    response_data = assessment.object_as_dict()
    response_data.update({"record_title": record.title})
    # or response_data = data.model_dump() and then:
    # response_data.update({"record_title": title, "category": category, "id_number": id_number})
    # but by returning UsersData object I make sure that all update changes has been made

    logger.debug(
        "Updated record: '%s' from %s (%s) by %s."
        % (id_number, category, record.title, user["username"])
    )

    return response_data


@router.delete("/delete/{category}/{id_number}", status_code=204)
async def delete_assessment(
    db: db_dependency,
    user: user_dependency,
    category: str = Path(enum=EntertainmentCategory.list_of_values()),
    id_number: int = Path(),
):
    logger.debug(
        "UsersData to delete: id number '%s' (%s category) created by %s."
        % (id_number, category, user["username"])
    )

    assessment = (
        db.query(UsersData)
        .filter(
            UsersData.category == category.capitalize(),
            UsersData.id_number == id_number,
        )
        .first()
    )
    if not assessment:
        raise RecordNotFoundException(
            extra_data=f"UsersData has no record of id_number '{id_number}' from {category} category."
        )

    # Verify if user is authorized to update a users_data
    check_if_author_or_admin(user, assessment)

    db.delete(assessment)
    db.commit()

    logger.debug(
        "UsersData with id_number '%s' (%s category) was successfully deleted by the '%s' user."
        % (id_number, category, user["username"])
    )
