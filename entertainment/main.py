import logging
import os
import traceback
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, HTTPException, Request  # noqa: F401
from fastapi.exception_handlers import http_exception_handler  # noqa: F401

from entertainment.database import create_db_tables, db_initial_data
from entertainment.logging_config import configure_logging
from entertainment.routers.auth import router as auth_router
from entertainment.routers.books import router as books_router
from entertainment.routers.games import router as games_router
from entertainment.routers.movies import router as movies_router
from entertainment.routers.songs import router as songs_router
from entertainment.routers.users import router as users_router
from entertainment.routers.users_data import router as users_data_router

LOG_FULL_TRACEBACK = False

# Setting logger
logger = logging.getLogger(__name__)
configure_logging()


# Starting the app with logging configuration
@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    create_db_tables()
    db_initial_data()
    yield


app = FastAPI(title="Entertainment API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(auth_router)
app.include_router(users_data_router)
app.include_router(books_router)
app.include_router(games_router)
app.include_router(movies_router)
app.include_router(songs_router)
app.include_router(users_router)


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
