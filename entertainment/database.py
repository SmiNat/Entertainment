import logging
import os
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from entertainment.config import config

logger = logging.getLogger(__name__)

# Setting the database
engine = create_engine(
    url=config.DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Creating database tables
def create_db_tables():
    Base.metadata.create_all(bind=engine)


# After creating the database, the app will check if the file with db exists
# and is populated with data from kaggle.com csv files (our external_data directory).
# If there are no records in the database (at the initial setup) the app will run
# the file csv_converter that converts csv files from our data directory
# into desired database structure and then it will fill our db file with initial data.
# Note: we are using config.py file to set the environment we currently work with,
# so instead of using .env file directly we access our environment variables
# through the config file. Therefore instead of getting the file path directly
# from .env file (like: str(os.environ.get("DEV_DATABASE_PATH"))) we use our
# config file (like: config.DATABASE_PATH).


# Checking if the the database has the initial data
def db_initial_data():
    # All data are from kaggle.com
    if os.path.exists(config.DATABASE_PATH):
        try:
            (
                sqlite3.connect(config.DATABASE_PATH)
                .cursor()
                .execute("SELECT count(*) FROM movies;")
                .fetchone()[0]
            )
        except sqlite3.OperationalError:
            logger.info("#️⃣  No initial database content.")
            logger.info("➡️  Updating a database... (can take a while)")
            import entertainment.csv_converter as csv_converter  # noqa: F401

            logger.info("✅ Database was successfully updated.")
        else:
            logger.debug("✅ Database with kaggle initial data is ready to use.")


# Creating a database connection
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
