# Entertainment API
API for movies, songs, books or games - check existing or add new records to the database.

Initial data source: [kaggle.com](https://www.kaggle.com/).

## Project setup

### To start API on your own working station follow the steps:
1) Download GitHub repository.
2) Install necessery packages from requirements.txt file.
3) Inside main folder run commend:

    *uvicorn entertainment.main:app --reload*

    This should create basic databese file (entertainment.db) at the first start of
    the application. After that FastAPI will use the same database to read, add,
    update and delete records.

    **Note:**

    At the first app launch, the csv_converter.py file will be used to create
    database file with tables filled with processed data from kaggle.com selected csv files.

    The original data are from:
    - https://www.kaggle.com/datasets/ishikajohari/best-books-10k-multi-genre-data (table: books)
    - https://www.kaggle.com/datasets/rahuldabholkar/steam-pc-games (table: games)
    - https://www.kaggle.com/datasets/ashpalsingh1525/imdb-movies-dataset (table: movies)
    - https://www.kaggle.com/datasets/joebeachcapital/30000-spotify-songs?select=spotify_songs.csv (table: songs)

    Some of the data was changed or deleted from the final database table.
    All changes were made in the csv_converter file.

    Because the project uses SQLite as the primary database, some data originally in the form of
    a list was converted to a string type, with values of which are separated by commas.

    **Handling db-journal error:**

    If by any chance an error concerning 'db-journal', such as:
    [*_rust_notify.WatchfilesRustInternalError: error in underlying watcher:
    IO error for operation on /.../entertainment.db-journal: No such file or directory*]
    will occure during the first attempt to run application (at the process when
    the new database is set up) and the database will not be successfully created,
    just terminate the proccess (optionally: delete entertainment.db file that
    was created during the proccess) and try again with the same commend:

    *uvicorn entertainment.main:app --reload*

4) Use OpenAPI on http://127.0.0.1:8000 to execute endpoints.

## Required
Python3.10