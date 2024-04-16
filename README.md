# Entertainment API
API for movies, songs, books or games - check existing or add new ones to the database.

Initial data source: [kaggle.com](https://www.kaggle.com/).

## Project setup

### To start API on your own working station follow the steps:
1) Download GitHub repository.
2) Install necessery packages from requirements.txt file.
3) Inside main folder run commend:
    *uvicorn entertainment.main:app --reload*
    This should create basic databese file (entertainment.db) at the first start of
    the application. After that FastAPI will use the same database to read, post and
    delete records.

    Handling db-journal error:
    If by any chance an error concerning 'db-journal' will occure
    [*_rust_notify.WatchfilesRustInternalError: error in underlying watcher:
    IO error for operation on /.../entertainment.db-journal: No such file or directory*]
    during the first attempt to run application (moment when new database is set up),
    just terminate the proccess, (optionally: delete entertainment.db file that
    was created during the proccess) and try again with commend:
    *uvicorn entertainment.main:app --reload*
4) Use OpenAPI on http://127.0.0.1:8000 to execute endpoints.

### Required
Python3.10