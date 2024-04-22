import datetime

from sqlalchemy import (
    # UUID,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from entertainment.database import Base


class Users(Base):
    __tablename__ = "users"

    # id = Column(UUID, primary_key=True, index=True, unique=True)
    id = Column(Integer, primary_key=True, index=True, unique=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )

    data = relationship("UserData", back_populates="user")


class UserData(Base):
    __tablename__ = "users_data"

    id = Column(Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    finished = Column(Boolean, default=False)
    vote = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )
    # user_id = Column(UUID, ForeignKey("users.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    movie_id = Column(Integer, ForeignKey("movies.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    song_id = Column(Integer, ForeignKey("songs.id"))
    game_id = Column(Integer, ForeignKey("games.id"))

    user = relationship("Users", back_populates="data")
    movie = relationship("Movies", back_populates="user")
    book = relationship("Books", back_populates="user")
    song = relationship("Songs", back_populates="user")
    game = relationship("Games", back_populates="user")


class Books(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    description = Column(Text)
    genres = Column(String, nullable=False)
    avg_rating = Column(Float)
    rating_reviews = Column(Integer)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="book")

    __table_args__ = (UniqueConstraint("title", "author", name="_book_uniqueness"),)


class Games(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(String, nullable=False)
    premiere = Column(Date, nullable=False)
    developer = Column(String, nullable=False)
    publisher = Column(String)
    genres = Column(String, nullable=False)
    type = Column(String)
    price_eur = Column(Float)
    price_discounted_eur = Column(Float)
    review_overall = Column(String)
    review_detailed = Column(String)
    reviews_number = Column(Integer)
    reviews_positive = Column(String)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="game")

    __table_args__ = (
        UniqueConstraint("title", "premiere", "developer", name="_game_uniqueness"),
    )


class Movies(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(String, nullable=False)
    premiere = Column(Date, nullable=False)
    score = Column(Float)
    genres = Column(String, nullable=False)
    overview = Column(Text)
    crew = Column(Text)
    orig_title = Column(String)
    orig_lang = Column(String)
    budget = Column(Float)
    revenue = Column(Float)
    country = Column(String)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="movie")

    __table_args__ = (UniqueConstraint("title", "premiere", name="_movie_uniqueness"),)


class Songs(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    song_id = Column(String, unique=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    song_popularity = Column(Integer)
    album_id = Column(String)
    album_name = Column(String, nullable=False)
    album_premiere = Column(Date)
    playlist_id = Column(String)
    playlist_name = Column(String)
    playlist_genre = Column(String)
    playlist_subgenre = Column(String)
    duration_ms = Column(Integer)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="song")

    __table_args__ = (
        UniqueConstraint("title", "artist", "album_name", name="_song_uniqueness"),
    )
