import logging
from unittest.mock import patch

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from sqlalchemy import func

from entertainment.models import Movies
from entertainment.routers.movies import fetch_accessible_movie_genres
from entertainment.tests.conftest import TestingSessionLocal
from entertainment.tests.utils_movies import (
    check_if_db_movies_table_is_not_empty,
    create_movie,
    movie_payload,
)
from entertainment.tests.utils_users import create_user_and_token

logger = logging.getLogger(__name__)

# COMMAND = "pytest entertainment/tests/routers/test_movies.py -s --log-cli-level=DEBUG"


def test_get_unique_row_data_with_fixture():
    with patch("entertainment.routers.movies.get_unique_row_data") as mock_function:
        mock_function.return_value = ["value1", "value2", "value3"]
        result = fetch_accessible_movie_genres(TestingSessionLocal())
        assert result == ["value1", "value2", "value3"]


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
    expected_result = ["Comedy", "Drama", "Family", "Music"]

    response = await async_client.get("/movies/genres")
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_movies_200_non_empty_db(async_client: AsyncClient):
    movie1 = create_movie(title="First Movie", score=9.2, genres=["comedy"])
    movie2 = create_movie(title="Second Movie", orig_title="sec. movie")
    movie3 = create_movie(score=2.7, premiere="2023-03-02", genres="drama")
    expected_result = {
        "number of movies": 3,
        "page": "1 of 1",
        "movies": [
            jsonable_encoder(movie1),
            jsonable_encoder(movie2),
            jsonable_encoder(movie3),
        ],
    }

    response = await async_client.get("/movies/all")
    assert response.status_code == 200
    assert expected_result == response.json()


@pytest.mark.anyio
async def test_get_all_movies_404_empty_db(async_client: AsyncClient):
    response = await async_client.get("/movies/all")
    assert response.status_code == 404
    assert "Movies not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_all_movies_pagination(async_client: AsyncClient):
    # Creating 3 movies in db with titles: "1", "2", "3"
    for x in range(1, 4):
        create_movie(title=str(x))

    # Making the request to the endpoint with page size and page number - empty page
    params = {"page_size": 10, "page_number": 2}
    expected_result = "Movies not found."
    response = await async_client.get("/movies/all", params=params)
    assert response.status_code == 404
    assert expected_result == response.json()["detail"]

    # Making the request to the endpoint with page size and page number - page with movies
    params = {"page_size": 1, "page_number": 3}
    expected_result = {
        "number of movies": 3,
        "page": "3 of 3",
        "movies": [
            {
                "id": 3,
                "score": 8.5,
                "overview": None,
                "orig_title": None,
                "budget": None,
                "country": "ES",
                "updated_by": None,
                "premiere": "2012-12-12",
                "title": "3",
                "genres": "Action, Mystery",
                "crew": "Test crew",
                "orig_lang": "Spanish",
                "revenue": None,
                "created_by": "John_Doe",
            }
        ],
    }
    response = await async_client.get("/movies/all", params=params)
    assert response.status_code == 200
    assert expected_result == response.json()

    # Page size out of range
    params = {"page_size": 222, "page_number": 3}
    response = await async_client.get("/movies/all", params=params)
    assert response.status_code == 422
    assert "Input should be less than or equal to 100" in response.text


@pytest.mark.anyio
async def test_search_movies_empty_db(async_client: AsyncClient):
    response = await async_client.get("/movies/search")
    expected_result = "Movies not found."
    assert response.status_code == 404
    assert expected_result == response.json()["detail"]


@pytest.mark.anyio
async def test_search_movies_non_empty_db(async_client: AsyncClient):
    movie1 = create_movie(title="First Movie", score=9.2, genres=["comedy", "action"])
    movie2 = create_movie(score=None, title="Second Movie", orig_title="sec. movie")
    movie3 = create_movie(score=2.7, premiere="2023-03-02", genres=["drama", "comedy"])

    # score >= 9.0 with exclude_empty_data = True
    response = await async_client.get(
        "/movies/search", params={"score_ge": 9.0, "exclude_empty_data": True}
    )
    expected_result = {
        "number of movies": 1,
        "page": "1 of 1",
        "movies": [jsonable_encoder(movie1)],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # score >= 9.0 with exclude_empty_data = False
    response = await async_client.get("/movies/search", params={"score_ge": 9.0})
    expected_result = {
        "number of movies": 2,
        "page": "1 of 1",
        "movies": [jsonable_encoder(movie1), jsonable_encoder(movie2)],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # title with "movie"
    response = await async_client.get("/movies/search", params={"title": "movie"})
    expected_result = {
        "number of movies": 3,
        "page": "1 of 1",
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
        "page": "1 of 1",
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
        "page": "1 of 1",
        "movies": [jsonable_encoder(movie1)],
    }
    assert response.status_code == 200
    assert expected_result == response.json()

    # country == "PL"
    response = await async_client.get("/movies/search", params={"country": "PL"})
    expected_result = "Movies not found."
    assert response.status_code == 404
    assert expected_result == response.json()["detail"]


@pytest.mark.anyio
async def test_search_movies_pagination(async_client: AsyncClient):
    # Creating 11 movies in db
    movies = []
    for x in range(1, 12):
        movies.append(create_movie(title=(str(x) + " movie")))

    # Calling the endpoint for the second page with all movies
    expected_result = {
        "number of movies": 11,
        "page": "2 of 2",
        "movies": [jsonable_encoder(movies[-1])],
    }
    response = await async_client.get(
        "/movies/search", params={"title": "movie", "page": 2}
    )
    assert response.status_code == 200
    assert expected_result == response.json()

    # Calling the endpoint for the second page with movie title '3 movie'
    expected_result = "Movies not found."
    response = await async_client.get(
        "/movies/search", params={"title": "3 movie", "page": 2}
    )
    assert response.status_code == 404
    assert expected_result == response.json()["detail"]


@pytest.mark.anyio
async def test_add_movie_201(async_client: AsyncClient, created_user_token: tuple):
    # Veryfying if the db movies table is empty
    assert check_if_db_movies_table_is_not_empty() is False

    user, token = created_user_token
    payload = movie_payload()

    with patch("entertainment.routers.movies.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Action", "Adventure", "Comedy", "Romance", "War"]

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
async def test_add_movie_401_if_not_authenticated(async_client: AsyncClient):
    payload = movie_payload()

    response = await async_client.post("/movies/add", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_title, comment",
    [
        ("Deadpool", "the same movie title"),
        ("deadpool", "the same movie title - case insensitive"),
        (" deadpool   ", "the same movie title - stripped from whitespaces"),
    ],
)
async def test_add_movie_422_not_unique_movie(
    async_client: AsyncClient,
    added_movie: Movies,
    created_token: str,
    invalid_title: str,
    comment: str,
):
    """The user can only create a movie with unique title and premiere date."""
    payload = movie_payload(
        title=invalid_title, premiere=added_movie.premiere.strftime("%Y-%m-%d")
    )

    with patch("entertainment.routers.movies.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Action", "Adventure", "Comedy", "Romance", "War"]
        response = await async_client.post(
            "/movies/add",
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        assert response.status_code == 422
        assert (
            "Unique constraint failed. A movie with that title and that premiere date "
            "already exists in the database." in response.json()["detail"]
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload, error_msg",
    [
        ({"title": None}, "Input should be a valid string"),
        ({"premiere": None}, "Input should be a valid date"),
        ({"genres": [None, None]}, "Input should be a valid string"),
        ({"score": 11}, "Input should be less than or equal to 10"),
        ({"premiere": "11-11-2011"}, "Input should be a valid date or datetime"),
        ({"revenue": "100k"}, "Input should be a valid number"),
        ({"country": "san escobar"}, "Invalid country name"),
        ({"orig_lang": "invalid"}, "Invalid language name"),
        (
            {"genres": ["invalid", "genre"]},
            "Invalid genre: check 'get genres' for list of accessible genres",
        ),
    ],
)
async def test_add_movie_422_invalid_input_data(
    async_client: AsyncClient,
    created_token: str,
    invalid_payload: dict,
    error_msg: str,
):
    payload = movie_payload(**invalid_payload)

    response = await async_client.post(
        "/movies/add",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert error_msg in response.text


@pytest.mark.parametrize(
    "value, comment",
    [
        ("Deadpool", "valid title, the same as in db"),
        ("deadpool", "valid title, lowercase"),
        ("   Deadpool  ", "valid title, with whitespaces"),
    ],
)
@pytest.mark.anyio
async def test_update_movie_202(
    async_client: AsyncClient,
    added_movie: Movies,
    created_user_token: tuple,
    value: str,
    comment: str,
):
    movie = added_movie
    assert movie.updated_by is None
    assert movie.score == 7.6
    assert movie.orig_title == "Deadpool"

    user, token = created_user_token
    title = value
    payload = {"score": 9.9, "orig_title": "Pool of death"}

    response = await async_client.patch(
        f"/movies/{title}/2016-02-11",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert response.json()["score"] == payload["score"]
    assert response.json()["updated_by"] == user["username"]


@pytest.mark.anyio
async def test_update_movie_401_if_not_authenticated(
    async_client: AsyncClient, added_movie: Movies
):
    payload = {"score": 9.9, "original title": "Pool of death"}

    response = await async_client.patch("/movies/Deadpool/2016-02-11", json=payload)
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()


@pytest.mark.anyio
async def test_update_movie_404_movie_not_found(
    async_client: AsyncClient, created_token: str
):
    payload = {"score": 9.9, "original title": "Pool of death"}

    response = await async_client.patch(
        "/movies/Deadpool/2016-02-11",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        "The record was not found in the database. Searched movie: 'Deadpool' (2016-02-11)."
        in response.json()["detail"]
    )


@pytest.mark.anyio
async def test_update_movie_202_update_by_the_admin(async_client: AsyncClient):
    """Test if user who is an admin but is not a movie record creator
    can update that movie."""
    # Creating movie record by John_Doe
    movie = create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    # Creating an admin user who is not the author of the movie to update
    admin_user, admin_token = create_user_and_token(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        role="admin",
    )

    payload = {
        "title": "Updated Movie",
        "premiere": "2022-01-01",
        "genres": ["comedy", "war", "Comedy", "action"],
    }

    with patch("entertainment.routers.movies.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Action", "Adventure", "Comedy", "Romance", "War"]
        response = await async_client.patch(
            f"/movies/{movie.title}/{movie.premiere}",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 202
        assert payload["title"] == response.json()["title"]
        assert admin_user.username == response.json()["updated_by"]


@pytest.mark.anyio
async def test_update_movie_403_update_by_the_user_who_is_not_the_movie_creator(
    async_client: AsyncClient, created_token: str
):
    # Creating movie record by John_Doe
    movie = create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    payload = {"title": movie.title, "premiere": movie.premiere.strftime("%Y-%m-%d")}

    response = await async_client.patch(
        f"/movies/{movie.title}/{movie.premiere}",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the database record "
        "can change or delete the record from the database" in response.text
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "title, comment",
    [
        ("Test Movie", "the same title and premiere as already registered movie"),
        (
            "test movie",
            "the same title (lowercase) and premiere as already registered movie",
        ),
        (
            "test movie   ",
            "the same title (withespaces) and premiere as already registered movie",
        ),
    ],
)
async def test_update_movie_422_not_unique_movie(
    async_client: AsyncClient,
    added_movie: Movies,
    created_token: str,
    title: str,
    comment: str,
):
    """Update cannot allow changes in title and premiere so that it could indicate
    to already existing movie in the database.
    The user can only change the title and premiere if they are unique."""
    # Creating other movie record in db (with the title of 'Test Movie' and premiere at 2011-11-11)
    create_movie()

    # Calling the endpoint with attempt to change the 'Deadpool'
    # movie title and premiere to the same as already existing one
    # (created by create_movie func)
    response = await async_client.patch(
        "/movies/Deadpool/2016-02-11",
        json={"title": title, "premiere": "2012-12-12"},
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    assert "UNIQUE constraint failed" in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload, expected_error",
    [
        ({"genres": [None, None]}, "No data input provided"),
        ({}, "No data input provided"),
    ],
)
async def test_update_movie_400_if_no_data_to_change(
    async_client: AsyncClient,
    added_movie: Movies,
    created_token: str,
    invalid_payload: dict,
    expected_error: str | None,
):
    payload = invalid_payload

    with patch("entertainment.routers.movies.get_unique_row_data") as mock_function:
        mock_function.return_value = ["Action", "Adventure", "Comedy", "Romance", "War"]
        response = await async_client.patch(
            "/movies/{0}/{1}".format(added_movie.title, added_movie.premiere),
            json=payload,
            headers={"Authorization": f"Bearer {created_token}"},
        )
        logger.debug("Response: %s" % response.json())
        assert response.status_code == 400
        assert expected_error in response.json()["detail"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "invalid_payload, error_msg",
    [
        ({"score": 11}, "Input should be less than or equal to 10"),
        ({"premiere": "11-11-2011"}, "Input should be a valid date or datetime"),
        ({"revenue": "100k"}, "Input should be a valid number"),
        ({"country": "san escobar"}, "Invalid country name"),
        ({"orig_lang": "invalid"}, "Invalid language name"),
        ({"genres": "invalid, drama"}, "Input should be a valid list"),
        (
            {"genres": ["invalid", "genre"]},
            "Invalid genre: check 'get genres' for list of accessible genres",
        ),
    ],
)
async def test_update_movie_422_incorrect_update_data(
    async_client: AsyncClient,
    added_movie: Movies,
    created_token: str,
    invalid_payload: dict,
    error_msg: str,
):
    payload = invalid_payload

    response = await async_client.patch(
        "/movies/Deadpool/2016-02-11",
        json=payload,
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 422
    logger.debug("Response detail: %s" % response.json()["detail"])
    assert error_msg in response.text


@pytest.mark.anyio
async def test_delete_movie_204(
    async_client: AsyncClient,
    added_movie: Movies,
    created_token: str,
):
    # Checking if the movie exists in db
    movie = (
        TestingSessionLocal()
        .query(Movies)
        .filter(
            Movies.premiere == added_movie.premiere,
            func.lower(Movies.title) == added_movie.title.lower().casefold(),
        )
        .first()
    )
    assert movie is not None
    logger.debug("Movie to delete: '%s' (%s)." % (movie.title, movie.premiere))

    # Calling the endpoint
    response = await async_client.delete(
        "/movies/{0}/{1}".format(added_movie.title, added_movie.premiere),
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 204

    # Checking if the movie no longer exists in db
    movie = (
        TestingSessionLocal().query(Movies).filter(Movies.title == "Deadpool").first()
    )
    assert movie is None


@pytest.mark.anyio
async def test_delete_movie_401_if_not_authenticated(
    async_client: AsyncClient, added_movie: Movies
):
    # Checking if the movie exists in db
    movie = (
        TestingSessionLocal()
        .query(Movies)
        .filter(Movies.premiere == "2016-02-11", Movies.title == "Deadpool")
        .first()
    )
    assert movie is not None
    logger.debug("Movie to delete: '%s' (%s)." % (movie.title, movie.premiere))

    # Calling the endpoint
    response = await async_client.delete(
        "/movies/Deadpool/2016-02-11",
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.content.decode()

    # Checking if the movie still exists in db
    movie = (
        TestingSessionLocal().query(Movies).filter(Movies.title == "Deadpool").first()
    )
    assert movie is not None


@pytest.mark.anyio
async def test_delete_movie_204_by_the_admin_user(async_client: AsyncClient):
    # Creating a movie by 'John_Doe'
    movie = create_movie()
    query = (
        TestingSessionLocal()
        .query(Movies)
        .filter(Movies.premiere == "2012-12-12", Movies.title == "Test Movie")
        .first()
    )
    assert query is not None
    assert "John_Doe" == query.created_by
    logger.debug("Movie to delete: '%s' (%s)." % (movie.title, movie.premiere))

    # Creating an admin user who is not the author of the movie to delete
    admin_user, admin_token = create_user_and_token(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        role="admin",
    )

    # Calling the endpoint by the admin user
    response = await async_client.delete(
        f"/movies/{movie.title}/{movie.premiere}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Checking if the movie no longer exists in db
    movie = (
        TestingSessionLocal().query(Movies).filter(Movies.title == "Test Movie").first()
    )
    assert movie is None


@pytest.mark.anyio
async def test_delete_movie_403_delete_by_the_user_who_is_not_the_movie_creator(
    async_client: AsyncClient, created_token: str
):
    # Creating a movie by 'John_Doe'
    movie = create_movie()
    assert check_if_db_movies_table_is_not_empty() is True

    logger.debug("Movie to delete: '%s' (%s)." % (movie.title, movie.premiere))

    # Calling the endpoint by 'testuser'
    response = await async_client.delete(
        f"/movies/{movie.title}/{movie.premiere}",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 403
    assert (
        "Only a user with the 'admin' role or the author of the database record "
        "can change or delete the record from the database" in response.json()["detail"]
    )

    # Checking if the movie still exists in db
    movie = (
        TestingSessionLocal().query(Movies).filter(Movies.title == "Test Movie").first()
    )
    assert movie is not None


@pytest.mark.anyio
async def test_delete_movie_404_movie_not_found(
    async_client: AsyncClient, created_token: str
):
    response = await async_client.delete(
        "/movies/deadpool/2004-02-13",
        headers={"Authorization": f"Bearer {created_token}"},
    )
    assert response.status_code == 404
    assert (
        "The record was not found in the database. Searched movie: 'deadpool' (2004-02-13)"
        in response.json()["detail"]
    )
