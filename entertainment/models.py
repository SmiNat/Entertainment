import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Session
from sqlalchemy.types import TypeDecorator

from entertainment.database import Base
from entertainment.enums import EntertainmentCategory, MyRate, WishlistCategory


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


class Books(Base):
    __tablename__ = "books"

    id = Column(
        Integer,
        primary_key=True,
        unique=True,
        autoincrement=True,
    )
    title = Column(StrippedString, nullable=False)
    author = Column(StrippedString, nullable=False)
    description = Column(Text)
    genres = Column(StrippedString, nullable=False)
    avg_rating = Column(Float)
    num_ratings = Column(Integer)
    first_published = Column(Date)
    created_by = Column(StrippedString, nullable=False)
    updated_by = Column(StrippedString)

    # user = relationship("UsersData", back_populates="book")

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

    id = Column(
        Integer,
        primary_key=True,
        unique=True,
        autoincrement=True,
    )
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
    created_by = Column(StrippedString, nullable=False)
    updated_by = Column(StrippedString)

    # user = relationship("UsersData", back_populates="game")

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
    created_by = Column(StrippedString, nullable=False)
    updated_by = Column(StrippedString)

    # user = relationship("UsersData", back_populates="movie")

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
    playlist_name = Column(StrippedString)
    playlist_genre = Column(StrippedString)
    playlist_subgenre = Column(StrippedString)
    duration_ms = Column(Integer)
    created_by = Column(StrippedString, nullable=False)
    updated_by = Column(StrippedString)

    # user = relationship("UsersData", back_populates="song")

    __table_args__ = (
        Index(
            "idx_songs_lowercased_title_artist_album",
            func.lower(title),
            func.lower(artist),
            func.lower(album_name),
            unique=True,
        ),
    )


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

    # data = relationship("UsersData", back_populates="user")

    __table_args__ = (
        Index(
            "idx_user_lowercased_username",
            func.lower(username),
            unique=True,
        ),
    )


CATEGORY_MODEL_MAP = {
    "Books": Books,
    "Games": Games,
    "Songs": Songs,
    "Movies": Movies,
}


class UsersData(Base):
    __tablename__ = "users_data"

    id = Column(Integer, primary_key=True, index=True, unique=True, autoincrement=True)
    category = Column(Enum(EntertainmentCategory), nullable=False)
    id_number = Column(Integer, nullable=False)
    db_record = Column(
        String,
        nullable=False,
        comment="A title or any other field that indicates assessed record.",
    )
    finished = Column(Boolean, default=False)
    wishlist = Column(Enum(WishlistCategory))
    watchlist = Column(Boolean, default=False)
    official_rate = Column(String())
    priv_rate = Column(Enum(MyRate))
    publ_comment = Column(String(500))
    priv_notes = Column(String(500))
    update_timestamp = Column(
        DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now()
    )
    created_by = Column(StrippedString, nullable=False)

    def get_related_record(self, session: Session):
        model = CATEGORY_MODEL_MAP.get(self.category)
        if model:
            return session.get(model, self.id_number)
        return None

    def object_as_dict(self):
        return dict((col, getattr(self, col)) for col in self.__table__.columns.keys())

    __table_args__ = (
        UniqueConstraint("category", "id_number", name="_record_uniqueness"),
    )

    # user_id = Column(Integer, ForeignKey("users.id"))
    # movie_id = Column(Integer, ForeignKey("movies.id"))
    # book_id = Column(Integer, ForeignKey("books.id"))
    # song_id = Column(Integer, ForeignKey("songs.id"))
    # game_id = Column(Integer, ForeignKey("games.id"))

    # user = relationship("Users", back_populates="data")
    # movie = relationship("Movies", back_populates="user")
    # book = relationship("Books", back_populates="user")
    # song = relationship("Songs", back_populates="user")
    # game = relationship("Games", back_populates="user")
