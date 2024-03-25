import datetime

from sqlalchemy import (
    UUID,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Date,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base


class Users(Base):
    __tablename__ = "users"

    user_id = Column(UUID, primary_key=True, index=True, unique=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    hashed_password = Column(String, unique=True, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
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

# Note: in below tables, next to the column specification there may be some
# additional comment with target structure, but as we are using
# existing databases from KAGGLE.COM, in our entertainmet.db in tables set
# based on KAGGLE.COM databases, the columns does not have additoonal
# restrictions implemented


class Books(Base):
    __tablename__ = "books"

    index = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(Text)  # nullable=False
    author = Column(Text)  # nullable=False
    description = Column(Text)
    genres = Column(Text)  # nullable=False
    avg_rating = Column(Float)
    rating_reviews = Column(Integer)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="book")

    __table_args__ = (UniqueConstraint("title", "author",
                                       name="_book_uniqueness"),)


class Games(Base):
    __tablename__ = "games"

    index = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(Text)  # nullable=False
    premiere = Column(Date)  # nullable=False
    developer = Column(Text)  # nullable=False
    publisher = Column(Text)
    genres = Column(Text)  # nullable=False
    type = Column(Text)
    price_eur = Column(Float)
    price_discounted_eur = Column(Float)
    review_overall = Column(Text)
    review_detailed = Column(Text)
    reviews_number = Column(Integer)
    reviews_positive = Column(Text)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="game")

    __table_args__ = (UniqueConstraint("title", "developer", "premiere",
                                       name="_game_uniqueness"),)


class Movies(Base):
    __tablename__ = "movies"

    index = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    title = Column(Text)  # nullable=False
    premiere = Column(Date)  # nullable=False
    score = Column(Float)
    genres = Column(Text)  # nullable=False
    overview = Column(Text)
    crew = Column(Text)
    orig_title = Column(Text)
    orig_lang = Column(Text)
    budget = Column(Float)
    revenue = Column(Float)
    country = Column(Text)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="movie")

    __table_args__ = (UniqueConstraint("title", "premiere",
                                       name="_movie_uniqueness"),)


class Songs(Base):
    __tablename__ = "songs"

    index = Column(Integer, primary_key=True, unique=True, autoincrement=True)
    song_id = Column(Text)  # unique=True
    title = Column(Text)  # nullable=False
    artist = Column(Text)  # nullable=False
    song_popularity = Column(Integer)
    album_id = Column(Text)  # unique=True
    album_name = Column(Text)  # nullable=False
    album_premiere = Column(Date)
    playlist_id = Column(Text)
    playlist_name = Column(Text)
    playlist_genre = Column(Text)
    playlist_subgenre = Column(Text)
    duration_ms = Column(Integer)
    created_by = Column(String)
    updated_by = Column(String)

    user = relationship("UserData", back_populates="song")

    __table_args__ = (UniqueConstraint("title", "artist", "album_name",
                                       name="_song_uniqueness"),)
