import logging

import pytest
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient

from entertainment.models import Movies, Users  # noqa
from entertainment.routers.movies import check_date, check_genre
from entertainment.tests.conftest import (  # noqa
    TestingSessionLocal,
    override_get_db,
)
from entertainment.tests.utils_movies import (
    check_if_db_movies_table_is_not_empty,
    create_movie,
    movie_payload,
)
from entertainment.tests.utils_users import create_user_and_token

logger = logging.getLogger(__name__)

# COMMAND = "pytest entertainment/tests/routers/test_movies.py -s --log-cli-level=DEBUG"


def test_check_date():
    invalid_date = "20-10-2020"
    # Example test case where date is invalid
    check_date("2020-10-20")

    # Example test case where date is invalid
    with pytest.raises(HTTPException) as exc_info:
        check_date(invalid_date)
    assert (
        "Invalid date type. Enter date in 'YYYY-MM-DD' format." in exc_info.value.detail
    )
    assert exc_info.value.status_code == 400


def test_check_genre():
    # Example test case where genres are valid
    check_genre(["action", "comedy"])

    # Example test case where genres are invalid
    with pytest.raises(HTTPException) as exc_info:
        check_genre(["romance", "history", "statistics"])
    assert exc_info.value.status_code == 403
    assert (
        "Invalid genre (check 'get movies genres' for list of accessible genres)"
        in exc_info.value.detail
    )


@pytest.mark.anyio
async def test_get_movies_genres_empty_db(async_client: AsyncClient):
    response = await async_client.get("/movies/genres")
    assert response.status_code == 200
    assert [] == response.json()


@pytest.mark.anyio
async def test_get_movies_genres_non_empty_db(async_client: AsyncClient):
    # Creating movies with genres in our db
    create_movie(title="First Movie", genres=["comedy"])
    create_movie(title="Second Movie", genres=["comedy", "music", "family"])
    create_movie(title="Third Movie", genres="drama")
    expected_result = ["comedy", "drama", "family", "music"]

    # Making the request to the endpoint
    response = await async_client.get("/movies/genres")
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_movies_empty_db(async_client: AsyncClient):
    response = await async_client.get("/movies/all")
    expected_result = {
        "number of movies": 0,
        "movies": [],
    }
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_movies_non_empty_db(async_client: AsyncClient):
    movie1 = create_movie(title="First Movie", score=9.2, genres=["comedy"])
    movie2 = create_movie(title="Second Movie", orig_title="sec. movie")
    movie3 = create_movie(score=2.7, premiere="2023-03-02", genres="drama")
    expected_result = {
        "number of movies": 3,
        "movies": [
            jsonable_encoder(movie1),
            jsonable_encoder(movie2),
            jsonable_encoder(movie3),
        ],
    }

    # Making the request to the endpoint
    response = await async_client.get("/movies/all")
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_movies_pagination(async_client: AsyncClient):
    # Creating 3 movies in db with titles: "1", "2", "3"
    for x in range(1, 4):
        create_movie(title=str(x))

    # Making the request to the endpoint with page size and page number - empty page
    params = {"page_size": 10, "page": 2}
    expected_result = {
        "number of movies": 3,
        "movies": [],
    }
    response = await async_client.get("/movies/all", params=params)
    assert response.status_code == 200
    assert expected_result == response.json()

    # Making the request to the endpoint with page size and page number - page with movies
    params = {"page_size": 1, "page": 3}
    expected_result = {
        "number of movies": 3,
        "movies": [
            {
                "id": 3,
                "score": 8.5,
                "overview": None,
                "orig_title": None,
                "budget": None,
                "country": "US",
                "updated_by": None,
                "premiere": "2011-11-11",
                "title": "3",
                "genres": "Action",
                "crew": "Test crew",
                "orig_lang": "English",
                "revenue": None,
                "created_by": "John_Doe",
            }
        ],
    }
    response = await async_client.get("/movies/all", params=params)
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_search_movies_empty_db(async_client: AsyncClient):
    response = await async_client.get("/movies/search")
    expected_result = {
        "number of movies": 0,
        "movies": [],
    }
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_search_movies_non_empty_db(async_client: AsyncClient):
    movie1 = create_movie(title="First Movie", score=9.2, genres=["comedy", "action"])
    movie2 = create_movie(title="Second Movie", orig_title="sec. movie")
    movie3 = create_movie(score=2.7, premiere="2023-03-02", genres=["drama", "comedy"])

    # score >= 9.0
    response = await async_client.get("/movies/search", params={"score_ge": 9.0})
    expected_result = {
        "number of movies": 1,
        "movies": [jsonable_encoder(movie1)],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # title with "movie"
    response = await async_client.get("/movies/search", params={"title": "movie"})
    expected_result = {
        "number of movies": 3,
        "movies": [
            jsonable_encoder(movie1),
            jsonable_encoder(movie2),
            jsonable_encoder(movie3),
        ],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # premiere before 2022
    response = await async_client.get(
        "/movies/search", params={"premiere_before": "2022-1-1"}
    )
    expected_result = {
        "number of movies": 2,
        "movies": [
            jsonable_encoder(movie1),
            jsonable_encoder(movie2),
        ],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # genre_primary == "action", genre_secondary == "comedy"
    response = await async_client.get(
        "/movies/search",
        params={"genre_primary": "action", "genre_secondary": "comedy"},
    )
    expected_result = {
        "number of movies": 1,
        "movies": [jsonable_encoder(movie1)],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # country == "PL"
    response = await async_client.get("/movies/search", params={"country": "PL"})
    expected_result = {
        "number of movies": 0,
        "movies": [],
    }
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_search_movies_pagination(async_client: AsyncClient):
    # Creating 11 movies in db
    movies = []
    for x in range(1, 12):
        movies.append(create_movie(title=(str(x) + " movie")))

    # Calling the endpoint for the second page with all movies
    expected_result = {
        "number of movies": 11,
        "movies": [jsonable_encoder(movies[-1])],
    }
    response = await async_client.get(
        "/movies/search", params={"title": "movie", "page": 2}
    )
    assert response.status_code == 200
    assert expected_result == response.json()

    # Calling the endpoint for the second page with movie title '3 movie'
    expected_result = {
        "number of movies": 1,
        "movies": [],
    }
    response = await async_client.get(
        "/movies/search", params={"title": "3 movie", "page": 2}
    )
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_add_movie_201(
    async_client: AsyncClient, created_user_token: tuple, mock_get_movies_genres
):
    # Veryfying if the db movies table is empty
    assert check_if_db_movies_table_is_not_empty() is False

    user, token = created_user_token
    payload = movie_payload()

    # Calling the endpoint by the user with the payload data
    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    # Veryfying if the db movies table is not empty
    assert check_if_db_movies_table_is_not_empty() is True

    # Veryfying if the db record has correct value of created_by_by field
    db_record = (
        TestingSessionLocal()
        .query(Movies)
        .filter(Movies.title == payload["title"])
        .first()
    )
    assert db_record.created_by == user["username"]


@pytest.mark.anyio
async def test_add_movie_401_if_not_authenticated(
    async_client: AsyncClient, mock_get_movies_genres
):
    payload = movie_payload()

    response = await async_client.post("/movies/add", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_add_movie_405_not_unique_movie(
    async_client: AsyncClient,
    added_movie: dict,
    created_token: str,
    mock_get_movies_genres,
):
    """The user can only create a movie with unique title and premiere date."""
    payload = movie_payload(title="Nigdy w życiu!", premiere="2004-02-13")

    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 405
    assert (
        "Movie 'Nigdy w życiu!' is already registered in the database"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_add_movie_403_invalid_genre(
    async_client: AsyncClient,
    created_token: str,
    mock_get_movies_genres,
):
    payload = movie_payload(genres=["invalid", "genre"])

    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 403
    assert (
        "Invalid genre (check 'get movies genres' for list of accessible genres)"
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_update_movie_202(
    async_client: AsyncClient,
    added_movie: dict,
    created_user_token: tuple,
):
    movie = added_movie
    assert movie["updated_by"] is None
    assert movie["score"] == 6.2
    assert movie["orig_title"] == "Nigdy w życiu!"

    user, token = created_user_token
    payload = {"score": 9.9, "orig_title": "Never, ever!"}

    response = await async_client.patch(
        "/movies/update/Nigdy w życiu!/2004-02-13",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert response.json()["score"] == payload["score"]
    assert response.json()["updated_by"] == user["username"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload, expected_error",
    [
        ({"score": 11}, "Input should be less than or equal to 10"),
        ({"premiere": "11-11-2011"}, "Input should be a valid date or datetime"),
        ({"revenue": "100k"}, "Input should be a valid number"),
    ],
)
async def test_update_movie_422_incorrect_update_data(
    async_client: AsyncClient,
    added_movie: dict,
    created_token: str,
    invalid_payload: dict,
    expected_error: str,
):
    payload = invalid_payload

    response = await async_client.patch(
        "/movies/update/Nigdy w życiu!/2004-02-13",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    logger.debug("Response detail: %s" % response.json()["detail"])
    assert expected_error in response.text


@pytest.mark.anyio
async def test_update_movie_400_not_unique_movie(
    async_client: AsyncClient, added_movie: dict, created_token: str
):
    """Update cannot allow changes in title and premiere so that it could indicate
    to already existing movie in the database.
    The user can only change the title and premiere if they are unique."""
    # Creating other movie record in db
    create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    payload = {
        "title": "Test Movie",
        "premiere": "2011-11-11",
    }  # !!!!!!!!!!!!!!!!!!!!!!!!!!!

    response = await async_client.patch(
        "/movies/update/Nigdy w życiu!/2004-02-13",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 400
    assert "UNIQUE constraint failed: movies.title, movies.premiere" in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status_code, genres, comment, expected_error",
    [
        (202, ["drama", "horror"], "correct", None),
        (202, ["drama", None, "horror"], "correct", None),
        (400, [None, None], "correct", "No data input provided"),
        (
            403,
            ["invalid", "drama"],
            "incorrect",
            "Invalid genre (check 'get movies genres' for list of accessible genres)",
        ),
        (422, "invalid, drama", "incorrect", "Input should be a valid list"),
    ],
)
async def test_update_movie_change_in_genres(
    async_client: AsyncClient,
    added_movie: dict,
    created_token: str,
    status_code: int,
    genres: str | list[str],
    comment: str,
    expected_error: str | None,
):
    payload = {"genres": genres}

    response = await async_client.patch(
        "/movies/update/Nigdy w życiu!/2004-02-13",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == status_code
    if response.status_code != 202:
        logger.debug("Response detail: %s" % response.json()["detail"])
        assert expected_error in response.text


@pytest.mark.anyio
async def test_update_movie_401_update_by_the_user_who_is_not_the_movie_creator(
    async_client: AsyncClient, created_token: str
):
    # Creating movie record by John_Doe
    create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    payload = {"title": "Test Movie", "premiere": "2011-11-11"}

    response = await async_client.patch(
        "/movies/update/Test Movie/2011-11-11",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 401
    assert "Only admin or author of a movie record can update a movie" in response.text


@pytest.mark.anyio
async def test_update_movie_202_update_by_the_admin(
    async_client: AsyncClient,
):
    """Test if user who is an admin but is not a movie record creator can update that movie."""
    # Creating movie record by John_Doe
    create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    # Creating a admin user who is not an author of a movie to update
    admin_user, admin_token = create_user_and_token(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        role="admin",
    )

    payload = {"title": "Updated Movie", "premiere": "2022-01-01"}

    response = await async_client.patch(
        "/movies/update/Test Movie/2011-11-11",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 202
    assert payload["title"] == response.json()["title"]
