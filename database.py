import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from logger import db_logger


# Creating database with data from KAGGLE.COM

db = "entertainment.db"
if os.path.exists(db):
    db_logger.info("➡️  Database already exists.")
else:
    db_logger.info("➡️  Creating a database... (can take a while)")
    import csv_converter

    if os.path.exists(db):
        db_logger.info("✅ Database 'entertainment' was successfully created.")

# Setting database for the project

SQLALCHEMY_DATABASE_URL = "sqlite:///./entertainment.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # echo=True  # for detail info about SQL commends
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
