import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from logger import db_logger

# Note: inital db data from KAGGLE.COM


def create_db(db_path: str):
    if os.path.exists(db_path):
        db_logger.info("➡️  Database already exists.")
    else:
        db_logger.info("➡️  Creating a database... (can take a while)")
        import csv_converter  # noqa: F401

        if os.path.exists(db_path):
            db_logger.info("✅ Database 'entertainment' was successfully created.")


def create_sqlite_engine(
    db_path: str, check_same_thread: bool = False, echo: bool = False, **kwargs
):
    return create_engine(
        db_path,
        connect_args={"check_same_thread": check_same_thread},
        echo=echo,
        **kwargs,
    )


# Setting database for the project

db = "entertainment.db"

create_db(db)

SQLALCHEMY_DATABASE_URL = "sqlite:///./entertainment.db"

engine = create_sqlite_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
