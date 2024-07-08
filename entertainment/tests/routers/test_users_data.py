import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy import text

from entertainment.models import Books, UsersData
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_users import create_user_and_token
from entertainment.tests.utils_users_data import assessment_payload, populate_database


@pytest.mark.anyio
async def test_search_200(
    async_client: AsyncClient,
    created_token: str,
):
    assessment1, assessment2, assessment3, assessment4 = populate_database()
    params = {}
    exp_response = {
        "number_of_records": 3,
        "page": "1 of 1",
        "records": [
            jsonable_encoder(
                assessment1,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
            jsonable_encoder(
                assessment2,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
            jsonable_encoder(
                assessment4,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
        ],
    }

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.anyio
async def test_search_404_if_no_assessment_made_by_the_user(
    async_client: AsyncClient,
):
    user, token = create_user_and_token("some_user")
    assessment1, assessment2, assessment3, assessment4 = populate_database()
    params = {}

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert (
        "User has not yet assessed any of the database records."
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_search_401_if_not_authorized(async_client: AsyncClient):
    assessment1, assessment2, assessment3, assessment4 = populate_database()
    params = {"finished": True}

    response = await async_client.get("/assess/search", params=params)
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_search_404_if_no_records_found(
    async_client: AsyncClient,
    created_token: str,
):
    assessment1, assessment2, assessment3, assessment4 = populate_database()
    params = {"finished": True, "priv_rate": "Awesome", "watchlist": True}

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "Records not found" in response.json()["detail"]


@pytest.mark.parametrize(
    "params, no_of_records, status_code, result",
    [
        ({}, 3, 200, ["a1", "a2", "a4"]),
        ({"finished": False}, 2, 200, ["a1", "a4"]),
        ({"finished": False, "category": "Books"}, 1, 200, ["a1"]),
        ({"priv_rate": "Awesome"}, 2, 200, ["a1", "a4"]),
        (
            {"priv_rate": "Awesome", "wishlist": "Maybe someday"},
            0,
            404,
            "Records not found",
        ),
        ({"category": "Games"}, 0, 404, "Records not found"),
        ({"watchlist": False}, 2, 200, ["a2", "a4"]),
        ({"watchlist": False, "priv_rate": "Awesome"}, 1, 200, ["a4"]),
    ],
)
@pytest.mark.anyio
async def test_search_with_different_search_scenarios(
    async_client: AsyncClient,
    created_token: str,
    params: dict,
    no_of_records: int,
    status_code: int,
    result: list[str] | str,
):
    assessment1, assessment2, assessment3, assessment4 = populate_database()
    assessment_mapping = {
        "a1": assessment1,
        "a2": assessment2,
        "a3": assessment3,
        "a4": assessment4,
    }
    params = params

    if status_code == 200:
        exp_result = {
            "number_of_records": no_of_records,
            "page": "1 of 1",
            "records": [
                jsonable_encoder(
                    assessment_mapping[x],
                    exclude_none=True,
                    exclude=["created_by", "update_timestamp"],
                )
                for x in result
            ],
        }

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == status_code
    if status_code == 200:
        assert exp_result == response.json()
    else:
        assert result in response.json()["detail"]


@pytest.mark.anyio
async def test_search_with_pagination(
    async_client: AsyncClient,
    created_token: str,
):
    assessment1, assessment2, assessment3, assessment4 = populate_database()

    # Page 1 of results
    params = {"page_number": 1}
    exp_response = {
        "number_of_records": 3,
        "page": "1 of 1",
        "records": [
            jsonable_encoder(
                assessment1,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
            jsonable_encoder(
                assessment2,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
            jsonable_encoder(
                assessment4,
                exclude_none=True,
                exclude=["created_by", "update_timestamp"],
            ),
        ],
    }

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert exp_response == response.json()

    # Page 2 of results
    params = {"page_number": 2}
    exp_response = "Records not found"

    response = await async_client.get(
        "/assess/search",
        params=params,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert exp_response in response.json()["detail"]


@pytest.mark.anyio
async def test_add_assessment_200(
    async_client: AsyncClient, added_book: Books, created_token: str
):
    payload = {
        "category": "Books",
        "id_number": 1,
        "finished": False,
        "wishlist": "Maybe someday",
        "watchlist": False,
        "official_rate": 3,
        "priv_rate": "Not bad",
        "publ_comment": None,
        "priv_notes": None,
    }

    exp_response = payload.copy()
    exp_response["official_rate"] = str(payload["official_rate"])
    exp_response["db_record"] = "New book"
    exp_response["id"] = 1

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.anyio
async def test_add_assessment_401_with_no_authorization(
    async_client: AsyncClient, added_book: Books
):
    payload = assessment_payload()
    response = await async_client.post("/assess/add", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.parametrize(
    "category",
    [("Books"), ("Games"), ("Movies"), ("Songs")],
)
@pytest.mark.anyio
async def test_add_assessment_404_with_no_record_to_assess(
    async_client: AsyncClient, added_book: Books, created_token: str, category: str
):
    payload = assessment_payload(category=category, id_number=2)

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        f"Searched record: id '2' in {category} category." in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_add_assessment_422_with_invalid_category(
    async_client: AsyncClient, added_book: Books, created_token: str
):
    payload = assessment_payload(category="invalid")

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert "Input should be 'Books', 'Games', 'Movies' or 'Songs'" in response.text


@pytest.mark.anyio
@pytest.mark.parametrize("official_rate", [(3), ("3")])
async def test_add_assessment_200_with_official_rate_as_int_or_string(
    async_client: AsyncClient,
    added_book: Books,
    created_token: str,
    official_rate: str | int,
):
    payload = assessment_payload(official_rate=official_rate)

    exp_response = payload.copy()
    exp_response["db_record"] = "New book"  # from added_book fixture
    exp_response["id"] = 1
    exp_response["official_rate"] = str(official_rate)

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert exp_response == response.json()


@pytest.mark.parametrize(
    "category, rate, exp_response",
    [
        ("Books", "Positive", "'Positive' is not a valid official rate"),
        ("Games", 1, "'1' is not a valid official rate"),
        ("Movies", "Positive", "'Positive' is not a valid official rate"),
        ("Songs", "any", "No official rate system provided for Songs category."),
    ],
)
@pytest.mark.anyio
async def test_add_assessment_400_with_invalid_official_rate(
    async_client: AsyncClient,
    created_token: str,
    category: str,
    rate: str | int,
    exp_response: str,
):
    payload = assessment_payload(category=category, official_rate=rate)

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 400
    assert exp_response in response.json()["detail"]


@pytest.mark.anyio
async def test_add_assessment_404_with_non_existing_attribute_title(
    async_client: AsyncClient, created_token: str, setup_test_table
):
    """Test if assessing record without title raises 404 with detail:
    '{data.category}' object has no attribute 'title'"""

    # Insert a movie record into the movies table (with no title column)
    with TestingSessionLocal() as db:
        db.execute(
            text("""
            INSERT INTO movies (id, crew, awards, director, category)
            VALUES (:id, :crew, :awards, :director, :category)
        """),
            {
                "id": 1,
                "crew": "John Doe",
                "awards": "Best Picture",
                "director": "Jane Smith",
                "category": "Movies",
            },
        )
        db.commit()

    payload = {
        "category": "Movies",
        "id_number": 1,
        "finished": False,
        "wishlist": None,
        "watchlist": False,
        "official_rate": None,
        "priv_rate": None,
        "publ_comment": None,
        "priv_notes": None,
    }

    response = await async_client.post(
        "/assess/add",
        headers={"Authorization": f"Bearer {created_token}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "'Movies' has no attribute 'title'."}


@pytest.mark.anyio
async def test_add_assessment_422_with_already_assessed_record(
    async_client: AsyncClient, created_token: str, added_book: Books
):
    record = UsersData(
        category="Books",
        id_number=added_book.id,
        db_record=added_book.title,
        finished=True,
        priv_rate="Awesome",
        created_by="testuser",
    )
    db = TestingSessionLocal()
    db.add(record)
    db.commit()
    db.close()

    assert db.query(UsersData).filter(UsersData.id == 1).first() is not None

    payload = assessment_payload(category="Books", id_number=added_book.id)

    response = await async_client.post(
        "/assess/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert (
        f"A record with id '{added_book.id}' from Books category has already been assessed."
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_update_assessment_patch_200(
    async_client: AsyncClient,
    created_token: str,
    added_book: Books,
    added_users_data: UsersData,
):
    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        "/assess/Books/1",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert "Test note" in response.json()["priv_notes"]
    assert "Books" in response.json()["category"]


@pytest.mark.anyio
async def test_update_assessment_patch_401_if_not_authenticated(
    async_client: AsyncClient, added_book: Books, added_users_data: UsersData
):
    payload = {"priv_notes": "Test note"}
    response = await async_client.patch("/assess/Books/1", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_assessment_patch_200_if_admin(
    async_client: AsyncClient,
    added_book: Books,
    added_users_data: UsersData,
):
    user, token = create_user_and_token(username="admin_user", role="admin")
    assert added_users_data.created_by != user.username
    assert added_users_data.priv_notes is None

    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        f"/assess/{added_users_data.category}/{added_users_data.id_number}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "Test note" in response.json()["priv_notes"]
    assert added_users_data.priv_notes is None


@pytest.mark.anyio
async def test_update_assessment_403_if_not_admin_or_not_author_of_the_record(
    async_client: AsyncClient,
    added_book: Books,
    added_users_data: UsersData,
):
    user, token = create_user_and_token(username="some_user", role="user")
    assert added_users_data.created_by != user.username

    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        f"/assess/{added_users_data.category}/{added_users_data.id_number}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "Only a user with the 'admin' role or the author of the database record "
    "can change or delete the record from the database" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_assessment_patch_404_if_non_existing_category(
    async_client: AsyncClient,
    created_token: str,
    added_users_data: UsersData,
):
    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        "/assess/xyz/1",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "'Xyz' category was not found in the database." in response.json()["detail"]


@pytest.mark.anyio
async def test_update_assessment_patch_404_if_no_books_record_found(
    async_client: AsyncClient,
    created_token: str,
    added_users_data: UsersData,
):
    book2 = TestingSessionLocal().query(Books).filter(Books.id == 2).first()
    assert book2 is None

    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        "/assess/Books/2",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert "Searched record: id '2' in Books category." in response.json()["detail"]


@pytest.mark.anyio
async def test_update_assessment_patch_404_if_no_usersdata_record_found(
    async_client: AsyncClient,
    created_token: str,
    added_book: Books,
):
    book = TestingSessionLocal().query(Books).filter(Books.id == 1).first()
    assert book is not None
    users_data = (
        TestingSessionLocal()
        .query(UsersData)
        .filter(UsersData.id_number == 1, UsersData.category == "Books")
        .first()
    )
    assert users_data is None

    payload = {"priv_notes": "Test note"}
    response = await async_client.patch(
        "/assess/Books/1",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        "UsersData has no record of id_number '1' from Books category."
        in response.json()["detail"]
    )


@pytest.mark.anyio
@pytest.mark.parametrize("official_rate", [(3), ("3")])
async def test_update_assessment_200_with_official_rate_as_int_or_string(
    async_client: AsyncClient,
    added_users_data: UsersData,
    created_token: str,
    official_rate: str | int,
):
    payload = {"official_rate": official_rate}

    response = await async_client.patch(
        "/assess/Books/1",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 200
    assert str(official_rate) in response.json()["official_rate"]


@pytest.mark.parametrize(
    "payload, status_code, exp_response",
    [
        (
            {"finished": "invalid"},
            422,
            "Input should be a valid boolean, unable to interpret input",
        ),
        (
            {"wishlist": "invalid"},
            422,
            "Input should be 'Black list', 'Maybe someday', ",
        ),
        (
            {"watchlist": "invalid"},
            422,
            "Input should be a valid boolean, unable to interpret input",
        ),
        ({"official_rate": "invalid"}, 400, "'invalid' is not a valid official rate"),
        ({"priv_rate": "invalid"}, 422, "Input should be 'Never again', 'Tragedy', "),
    ],
)
@pytest.mark.anyio
async def test_update_assessment_patch_incorrect_data(
    async_client: AsyncClient,
    created_token: str,
    added_users_data: UsersData,
    payload: dict,
    status_code: int,
    exp_response: str,
):
    payload = payload
    response = await async_client.patch(
        "/assess/Books/1",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == status_code
    assert exp_response in response.text


@pytest.mark.anyio
async def test_delete_assessment_204(
    async_client: AsyncClient,
    created_token: str,
    added_users_data: UsersData,
):
    response = await async_client.delete(
        "/assess/Books/1",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_assessment_401_if_not_authorized(
    async_client: AsyncClient,
    added_users_data: UsersData,
):
    response = await async_client.delete("/assess/Books/1")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.anyio
async def test_delete_assessment_404_if_no_record_found(
    async_client: AsyncClient,
    created_token: str,
):
    response = await async_client.delete(
        "/assess/Books/1",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        "UsersData has no record of id_number '1' from Books category." in response.text
    )


@pytest.mark.anyio
async def test_delete_assessment_403_if_not_admin_or_record_author(
    async_client: AsyncClient,
    added_users_data: UsersData,
):
    user, token = create_user_and_token(username="some_user", role="user")
    assert added_users_data.created_by != user.username

    response = await async_client.delete(
        "/assess/Books/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "Only a user with the 'admin' role or the author of the database record "
    "can change or delete the record from the database." in response.text


@pytest.mark.anyio
async def test_delete_assessment_204_if_deleted_by_admin(
    async_client: AsyncClient,
    added_users_data: UsersData,
):
    user, token = create_user_and_token(username="admin_user", role="admin")
    assert added_users_data.created_by != user.username

    response = await async_client.delete(
        "/assess/Books/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
