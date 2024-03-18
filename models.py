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
    role = Column(String)
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
    book_id = Column(Integer, ForeignKey("books.index"))
    song_id = Column(Integer, ForeignKey("songs.index"))
    game_id = Column(Integer, ForeignKey("games.index"))

    user = relationship("Users", back_populates="data")
    movie = relationship("Movies", back_populates="user")
    book = relationship("Books", back_populates="user")
    song = relationship("Songs", back_populates="user")
    game = relationship("Games", back_populates="user")


class Books(Base):
    __tablename__ = "books"

    index = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    book = Column(String)
    author = Column(String)
    description = Column(String, nullable=True)
    genres = Column(String)
    avg_rating = Column(Float, nullable=True)
    num_ratings = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    user = relationship("UserData", back_populates="book")


class Games(Base):
    __tablename__ = "games"

    index = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    title = Column(String)
    release_date = Column(String)
    developer = Column(String, nullable=True)
    publisher = Column(String, nullable=True)
    genres = Column(String)
    game_type = Column(String, nullable=True)
    price = Column(String, nullable=True)
    price_discounted = Column(String, nullable=True)
    overall_review = Column(String, nullable=True)
    detailed_review = Column(String, nullable=True)
    reviews = Column(String, nullable=True)
    percent_positive = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    user = relationship("UserData", back_populates="game")


class Movies(Base):
    __tablename__ = "movies"

    index = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    title = Column(String)
    premiere = Column(String)
    score = Column(Float)
    genre = Column(String)
    overview = Column(String, nullable=True)
    crew = Column(String, nullable=True)
    orig_title = Column(String, nullable=True)
    orig_lang = Column(String, nullable=True)
    budget = Column(Float, nullable=True)
    revenue = Column(Float, nullable=True)
    country = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    user = relationship("UserData", back_populates="movie")


class Songs(Base):
    __tablename__ = "songs"

    index = Column(
        Integer, primary_key=True, index=True, unique=True, autoincrement=True
    )
    year = Column(Integer)
    track_id = Column(String, nullable=True)
    track_name = Column(String)
    track_popularity = Column(Integer, nullable=True)
    album = Column(String)
    artist_id = Column(String, nullable=True)
    artist_name = Column(String)
    artist_genres = Column(String)
    artist_popularity = Column(Integer, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

    user = relationship("UserData", back_populates="song")
