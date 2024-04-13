from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import config


def create_sqlite_engine(
    db_path: str, check_same_thread: bool = False, echo: bool = False, **kwargs
):
    return create_engine(
        db_path,
        connect_args={"check_same_thread": check_same_thread},
        echo=echo,
        **kwargs,
    )


engine = create_sqlite_engine(config.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
