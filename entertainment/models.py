import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from entertainment.database import Base


class StrippedString(TypeDecorator):
    """For stripping trailing and leading whitespaces from string values
    before saving a record to the database."""

    impl = String

    cache_ok = True

    def process_bind_param(self, value, dialect):
        # In case of nullable string fields and passing None
        return value.strip() if value else value

    def copy(self, **kw):
        return StrippedString(self.impl.length)


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, unique=True)
    username = Column(StrippedString, unique=True, index=True, nullable=False)
    email = Column(StrippedString, unique=True, index=True, nullable=False)
    first_name = Column(StrippedString, nullable=True)
    last_name = Column(StrippedString, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(StrippedString, default="user")
    is_active = Column(Boolean, default=True)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )

    data = relationship("UserData", back_populates="user")

    __table_args__ = (
        Index(
            "idx_user_lowercased_username",
            func.lower(username),
            unique=True,
        ),
    )


class UserData(Base):
    __tablename__ = "users_data"

    id = Column(Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    finished = Column(Boolean, default=False)
    vote = Column(Integer, nullable=True)
    notes = Column(StrippedString, nullable=True)
    create_timestamp = Column(DateTime, default=datetime.datetime.now())
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )

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
    title = Column(StrippedString, nullable=False)
    author = Column(StrippedString, nullable=False)
    description = Column(Text)
    genres = Column(StrippedString, nullable=False)
    avg_rating = Column(Float)
    num_ratings = Column(Integer)
    first_published = Column(Date)
    created_by = Column(StrippedString)
    updated_by = Column(StrippedString)

    user = relationship("UserData", back_populates="book")

    __table_args__ = (
        Index(
            "idx_books_lowercased_title_author",
            func.lower(title),
            func.lower(author),
            unique=True,
        ),
    )


class Games(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(StrippedString, nullable=False)
    premiere = Column(Date, nullable=False)
    developer = Column(StrippedString, nullable=False)
    publisher = Column(StrippedString)
    genres = Column(StrippedString, nullable=False)
    game_type = Column(StrippedString)
    price_eur = Column(Float)
    price_discounted_eur = Column(Float)
    review_overall = Column(StrippedString)
    review_detailed = Column(StrippedString)
    reviews_number = Column(Integer)
    reviews_positive = Column(Float)
    created_by = Column(StrippedString)
    updated_by = Column(StrippedString)

    user = relationship("UserData", back_populates="game")

    __table_args__ = (
        Index(
            "idx_games_lowercased_title_premiere_developer",
            func.lower(title),
            premiere,
            func.lower(developer),
            unique=True,
        ),
    )


class Movies(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(StrippedString, nullable=False)
    premiere = Column(Date, nullable=False)
    score = Column(Float)
    genres = Column(StrippedString, nullable=False)
    overview = Column(Text)
    crew = Column(Text)
    orig_title = Column(StrippedString)
    orig_lang = Column(StrippedString)
    budget = Column(Float)
    revenue = Column(Float)
    country = Column(StrippedString)
    created_by = Column(StrippedString)
    updated_by = Column(StrippedString)

    user = relationship("UserData", back_populates="movie")

    __table_args__ = (
        Index(
            "idx_movies_lowercased_title_premiere",
            func.lower(title),
            premiere,
            unique=True,
        ),
    )


class Songs(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    song_id = Column(String, unique=True)
    title = Column(StrippedString, nullable=False)
    artist = Column(StrippedString, nullable=False)
    song_popularity = Column(Integer)
    album_id = Column(String)
    album_name = Column(StrippedString, nullable=False)
    album_premiere = Column(Date)
    playlist_id = Column(String)
    playlist_name = Column(StrippedString)
    playlist_genre = Column(StrippedString)
    playlist_subgenre = Column(StrippedString)
    duration_ms = Column(Integer)
    created_by = Column(StrippedString)
    updated_by = Column(StrippedString)

    user = relationship("UserData", back_populates="song")

    __table_args__ = (
        Index(
            "idx_songs_lowercased_title_artist_album_duration",
            func.lower(title),
            func.lower(artist),
            func.lower(album_name),
            duration_ms,
            unique=True,
        ),
    )
