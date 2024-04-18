import logging
import os
import sqlite3
import traceback
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException, Request  # noqa: F401
from fastapi.exception_handlers import http_exception_handler  # noqa: F401

from entertainment.config import config
from entertainment.database import Base, engine
from entertainment.logging_config import configure_logging
from entertainment.routers import auth, movies, users

# Setting logger
LOG_FULL_TRACEBACK = False

logger = logging.getLogger(__name__)

configure_logging()


# Creating database tables
Base.metadata.create_all(bind=engine)

# After creating the database, the app will check if the file with db exists
# and is populated with data from kaggle.com csv files (our data directory).
# If there are no records in the database (at the initial setup) the app will run
# the file csv_converter that converts csv files from our data directory
# into desired database structure and then it will fill our db file with initial data.
# Note: we are using config.py file to set the environment we currently work with,
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


# Starting the app with logging configuration
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(title="Entertainment API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(users.router)


# Logging the HTTPExceptions
# Note: The following code allows you to log HTTPErrors without actually having
# to write a logger in each HTTPException statement.
# The downside of this solution is that logs no longer have a specific logger name
# and filename because all loggers are activated by the code in the main.py file.
# To receive more information about the exception, tha app will add extra data
# to the logger in http_exception_handle_logging function so that it contain either
# full traceback of an error or selected information from that traceback.


def extract_traceback_data():
    traceback_calls = traceback.format_exc().split("File")
    app_dir = os.path.dirname(os.path.abspath(__file__))
    current_dir = os.path.normpath(__file__)
    logger_calls = []
    for call in traceback_calls:
        traceback_call = {
            "filename": None,
            "lineno": None,
            "func": None,
        }
        if app_dir in call and current_dir not in call:
            data = call.split("\n")
            data = [element.strip() for element in data]
            path = data[0].split("/entertainment")[1].split('"')[0]
            traceback_call["filename"] = path

            if ", line " in data[0]:
                line = data[0].split(", line ")[1].split(",")[0]
                traceback_call["lineno"] = line
            if ", in " in data[0]:
                func = data[0].split(", in ")[1]
                traceback_call["func"] = func

            if "raise HTTPException" in data[1]:
                try:
                    status_code = data[1][
                        data[1].index("_") + 1 : data[1].index("_") + 4
                    ]
                    traceback_call["status_code"] = status_code
                    message = data[1][data[1].index(', "') + 1 : -2]
                    traceback_call["message"] = message
                except ValueError:
                    pass

            logger_calls.append(traceback_call)

    return logger_calls


@app.exception_handler(HTTPException)
async def http_exception_handle_logging(
    request: Request,
    exc: HTTPException,
    display_traceback: bool = LOG_FULL_TRACEBACK,
):
    if display_traceback:
        # Get the full stack trace information
        additional_info = traceback.format_exc().split("\n")
    else:
        # Get the filename, line number an function name where the exception
        # was raised within your application
        additional_info = extract_traceback_data()

    # Log the HTTPException with stack trace
    logger.error(
        f"HTTPException: {exc.status_code}, {exc.detail}",
        extra={"additional information": additional_info},
    )

    return await http_exception_handler(request, exc)
