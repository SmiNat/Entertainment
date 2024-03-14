import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        # logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ],
)

# Creating database with data from KAGGLE.COM

db = "entertainment.db"
if os.path.exists(db):
    logging.info("➡️ Database already exists.")
else:
    logging.info("➡️ Creating a database... (can take a while)")
    import csv_converter

    if os.path.exists(db):
        logging.info("✅ Database 'entertainment' created.")

# Setting database for the project

SQLALCHEMY_DATABASE_URL = "sqlite:///./entertainment.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
