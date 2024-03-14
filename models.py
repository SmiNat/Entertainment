import datetime

from sqlalchemy import (UUID, Boolean, Column, DateTime, Float, ForeignKey,
                        Integer, String)
from sqlalchemy.orm import relationship

from database import Base


class Users(Base):
    __tablename__ = "users"

    user_id = Column(UUID, primary_key=True, index=True, unique=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )

    data = relationship("UserData", back_populates="user")


class UserData(Base):
    __tablename__ = "users_data"

    data_id = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    finished = Column(Boolean, default=False)
    vote = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )
    user_id = Column(UUID, ForeignKey("users.user_id"))
    movie_id = Column(Integer, ForeignKey("movies.index"))

    user = relationship("Users", back_populates="data")
    movie = relationship("Movies", back_populates="user")


class Books(Base):
    __tablename__ = "books"

    index = Column(Integer, primary_key=True, index=True, unique=True)
    book = Column(String)
    author = Column(String)
    description = Column(String)
    genres = Column(String)
    avg_rating = Column(Float)
    num_ratings = Column(String)


class Games(Base):
    __tablename__ = "games"
    index = Column(Integer, primary_key=True, index=True, unique=True)
    title = Column(String)
    release_date = Column(String)
    developer = Column(String)
    publisher = Column(String)
    genres = Column(String)
    game_type = Column(String)
    price = Column(String)
    price_discounted = Column(String)
    overall_review = Column(String)
    detailed_review = Column(String)
    reviews = Column(String)
    percent_positive = Column(String)


class Movies(Base):
    __tablename__ = "movies"

    index = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    title = Column(String)
    premiere = Column(String)
    score = Column(Float)
    genre = Column(String)
    overview = Column(String)
    crew = Column(String)
    orig_title = Column(String)
    orig_lang = Column(String)
    budget = Column(Float)
    revenue = Column(Float)
    country = Column(String)

    user = relationship("UserData", back_populates="movie")


class Songs(Base):
    __tablename__ = "songs"

    index = Column(Integer, primary_key=True, index=True, unique=True)
    year = Column(Integer)
    track_id = Column(String)
    track_name = Column(String)
    track_popularity = Column(Integer)
    album = Column(String)
    artist_id = Column(String)
    artist_name = Column(String)
    artist_genres = Column(String)
    artist_popularity = Column(Integer)
    duration_ms = Column(Float)
