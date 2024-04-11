from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def create_sqlite_engine(
    db_path: str, check_same_thread: bool = False, echo: bool = False, **kwargs
):
    return create_engine(
        db_path,
        connect_args={"check_same_thread": check_same_thread},
        echo=echo,
        **kwargs,
    )


SQLALCHEMY_DATABASE_URL = "sqlite:///./entertainment.db"

engine = create_sqlite_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
