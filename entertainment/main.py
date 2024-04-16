import logging
import os
import sqlite3
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler

from entertainment.config import config
from entertainment.database import Base, engine
from entertainment.logging_config import configure_logging
from entertainment.routers import auth, movies, users

logger = logging.getLogger(__name__)

configure_logging()


Base.metadata.create_all(bind=engine)


# After creating a database, we will check if the file with db exists
# and is populated with data from kaggle.com csv files (from our data directory).
# If there are no records in the database (at the initial setup) then we will run
# the file csv_converter that converts csv files from our data directory
# into desired database structure and we will fill our db file with initial data.
# Note: we are using config.py file to set the environment we cureently work with,
# so instead of using .env file directly we access our environment variables
# through the config file. Therefore instead of getting the file path directly
# from .env file (like: str(os.environ.get("DEV_DATABASE_PATH"))) we use our
# config file (like: config.DATABASE_PATH).

if os.path.exists(config.DATABASE_PATH):
    if not (
        sqlite3.connect(config.DATABASE_PATH)
        .cursor()
        .execute("SELECT count(*) FROM movies;")
        .fetchone()[0]
    ):
        logger.info("#️⃣  No initial database content.")
        logger.info("➡️  Updating a database... (can take a while)")
        import entertainment.csv_converter as csv_converter  # noqa: F401

        logger.info("✅ Database was successfully updated.")
    else:
        logger.debug("✅ Database with kaggle initial data is ready to use.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="Entertainment API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(users.router)


@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc):
    logger.error("HTTPException: %s %s" % (exc.status_code, exc.detail))
    return await http_exception_handler(request, exc)
