import os
import sqlite3

from fastapi import FastAPI

from database import Base, engine
from logger import db_logger
from routers import auth, movies, users

app = FastAPI(title="Entertainment API", version="0.1.0")


Base.metadata.create_all(bind=engine)

if os.path.exists(str(os.environ.get("DATABASE"))):
    if not (
        sqlite3.connect(str(os.environ.get("DATABASE")))
        .cursor()
        .execute("SELECT count(*) FROM movies;")
        .fetchone()[0]
    ):
        db_logger.info("➡️  Updating a database... (can take a while)")
        import csv_converter  # noqa: F401

        db_logger.info("✅ Database 'entertainment' was successfully updated.")


app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(users.router)
