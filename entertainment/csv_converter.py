# Note: all csv files are from kaggle.com.
# To fulfill database tables structure and restrictions specified in models.py file
# a few changes are implemented in temporary tables from csv files before
# inserting the final data to final db tables.

import logging
import os
import sqlite3

import chardet
import pandas as pd

pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 15)

logger = logging.getLogger(__name__)


def create_table(table_name: str, query: str, connection: sqlite3.Connection) -> None:
    """Creates a new table in the database if it does not exists."""
    try:
        connection.execute("SELECT count(*) FROM %s LIMIT 1;" % table_name)
    except sqlite3.OperationalError:
        logger.debug("Creating %s table..." % table_name)
        connection.execute(query)
        connection.commit()


def execute_commands(commands: dict[str:str], connection: sqlite3.Connection) -> None:
    """Execute commands on SQLite database on already established connection.
    Note: does not open or close connection to the database, just uses the existing one.
    Args:
        commands (dict): dictionary of command names (keys) and SQL
            command statement (values).
        connection (sqlite3.Connection): already established connection to
            SQLite database.
    """
    logger.debug("Transforming kaggle table...")
    for command in commands.values():
        if isinstance(command, list):
            for single_command in command:
                connection.execute(single_command)
        else:
            connection.execute(command)
    connection.commit()


def switch_and_drop_table(table_from: str, table_to: str):
    """Inserts data to funall tables and deletes temporary tables from database."""
    logger.debug(
        f"Inserting data from kaggle {table_from!r} table to {table_to!r} final table..."
    )

    copy_db = f"INSERT INTO {table_to} SELECT * FROM {table_from};"
    conn.execute(copy_db)
    conn.commit()

    drop_db = f"DROP TABLE IF EXISTS {table_from};"
    conn.execute(drop_db)
    conn.commit()
    logger.debug(f"Table {table_to!r} ready to use.")


# Opening connection to a database
conn = sqlite3.connect(str(os.environ.get("DEV_DATABASE_PATH")))
cursor = conn.cursor()


# Database content

# Games table
create_table_query = """
    CREATE TABLE games (
        id                  INTEGER     PRIMARY KEY UNIQUE,
        title               VARCHAR     NOT NULL,
        premiere            DATE        NOT NULL,
        developer           VARCHAR     NOT NULL,
        publisher           VARCHAR,
        genres              VARCHAR     NOT NULL,
        type                VARCHAR,
        price_eur           FLOAT,
        price_discounted_eur FLOAT,
        review_overall      VARCHAR,
        review_detailed     VARCHAR,
        reviews_number      INTEGER,
        reviews_positive    VARCHAR,
        created_by          VARCHAR,
        updated_by          VARCHAR,
        UNIQUE(title, premiere, developer)
    );
"""
create_table("games", create_table_query, conn)

csv_file = "external_data/games_data.csv"
with open(csv_file, "rb") as raw_data:
    result = chardet.detect(raw_data.read(100000))
logger.debug("File 'games_data.csv' encoding: %s." % result)
df = pd.read_csv(csv_file, encoding="Windows-1252", low_memory=False)
df.columns = df.columns.str.strip()
df.to_sql("games_temp", conn, if_exists="replace")

# Note: The PRICE is in INR - this will be converted to EUR @0.011 exchange rate

db_games_temp = {
    "drop columns #1": [
        "ALTER TABLE games_temp DROP COLUMN id;",
        "ALTER TABLE games_temp DROP COLUMN win_support;",
        "ALTER TABLE games_temp DROP COLUMN mac_support;",
        "ALTER TABLE games_temp DROP COLUMN lin_support;",
    ],
    "delete rows": [
        """
        DELETE FROM games_temp
        WHERE overall_review IS NULL AND detailed_review IS NULL;
        """,
        """
        DELETE FROM games_temp
        WHERE overall_review LIKE "1%" OR overall_review == "Free to play";
        """,
        "DELETE FROM games_temp WHERE title IS NULL;",
        "DELETE FROM games_temp WHERE developer IS NULL;",
        "DELETE FROM games_temp WHERE release_date IS NULL;",
        "DELETE FROM games_temp WHERE genres IS NULL;",
        "DELETE FROM games_temp WHERE title LIKE '%???%';",
    ],
    "add columns": [
        "ALTER TABLE games_temp ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE games_temp ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE games_temp
        SET developer = replace(developer, ';', ', ')
        WHERE developer LIKE '%;%';
        """,
        """
        UPDATE games_temp
        SET publisher = replace(publisher, ';', ', ')
        WHERE publisher LIKE '%;%';
        """,
        """
        UPDATE games_temp
        SET genres = replace(genres, ';', ', ')
        WHERE genres LIKE '%;%';
        """,
        """
        UPDATE games_temp
        SET multiplayer_or_singleplayer = replace(multiplayer_or_singleplayer, ';', ', ')
        WHERE multiplayer_or_singleplayer LIKE '%;%';
        """,
        "UPDATE games_temp SET price = replace(price, ',', '') WHERE price LIKE '%,%';",
        "UPDATE games_temp SET price = round(price*0.011, 2) WHERE price > 0;",
        """
        UPDATE games_temp
        SET dc_price = replace(dc_price, ',', '')
        WHERE dc_price LIKE '%,%';
        """,
        "UPDATE games_temp SET dc_price = round(dc_price*0.011, 2) WHERE dc_price > 0;",
        """
        UPDATE games_temp
        SET created_by = "www.kaggle.com - rahuldabholkar"
        WHERE created_by is NULL;
        """,
    ],
    "rename columns": [
        "ALTER TABLE games_temp RENAME COLUMN overall_review TO review_overall;",
        "ALTER TABLE games_temp RENAME COLUMN detailed_review TO review_detailed;",
        "ALTER TABLE games_temp RENAME COLUMN percent_positive TO reviews_positive;",
        "ALTER TABLE games_temp RENAME COLUMN multiplayer_or_singleplayer TO type;",
        "ALTER TABLE games_temp RENAME COLUMN release_date TO premiere;",
        "ALTER TABLE games_temp RENAME COLUMN price TO price_eur;",
        "ALTER TABLE games_temp RENAME COLUMN dc_price TO price_discounted_eur;",
        "ALTER TABLE games_temp RENAME COLUMN reviews TO reviews_number;",
    ],
    "drop duplicate rows": [
        """
        DELETE FROM  games_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM games_temp
        GROUP BY lower(title), premiere, lower(developer)
        );
        """
    ],
}
execute_commands(db_games_temp, conn)
switch_and_drop_table("games_temp", "games")


# Songs table
create_table_query = """
    CREATE TABLE songs (
        id                  INTEGER     PRIMARY KEY UNIQUE,
        song_id             VARCHAR     UNIQUE,
        title               VARCHAR     NOT NULL,
        artist              VARCHAR     NOT NULL,
        song_popularity     INTEGER,
        album_id            VARCHAR,
        album_name          VARCHAR     NOT NULL,
        album_premiere      DATE,
        playlist_id         VARCHAR,
        playlist_name       VARCHAR,
        playlist_genre      VARCHAR,
        playlist_subgenre   VARCHAR,
        duration_ms         INTEGER,
        created_by          VARCHAR,
        updated_by          VARCHAR,
        UNIQUE(title, artist, album_name, duration_ms)
    );
"""
create_table("songs", create_table_query, conn)

csv_file = "external_data/spotify_songs.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("songs_temp", conn, if_exists="replace")

db_songs_temp = {
    "drop columns": [
        "ALTER TABLE songs_temp DROP COLUMN danceability;",
        "ALTER TABLE songs_temp DROP COLUMN energy;",
        "ALTER TABLE songs_temp DROP COLUMN key;",
        "ALTER TABLE songs_temp DROP COLUMN loudness;",
        "ALTER TABLE songs_temp DROP COLUMN mode;",
        "ALTER TABLE songs_temp DROP COLUMN speechiness;",
        "ALTER TABLE songs_temp DROP COLUMN acousticness;",
        "ALTER TABLE songs_temp DROP COLUMN instrumentalness;",
        "ALTER TABLE songs_temp DROP COLUMN liveness;",
        "ALTER TABLE songs_temp DROP COLUMN valence;",
        "ALTER TABLE songs_temp DROP COLUMN tempo;",
    ],
    "add columns": [
        "ALTER TABLE songs_temp ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE songs_temp ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE songs_temp
        SET created_by = "www.kaggle.com - joebeachcapital"
        WHERE created_by is NULL;
        """,
        "UPDATE songs_temp SET track_name = '---' WHERE track_name IS NULL;",
        "UPDATE songs_temp SET track_artist = '---' WHERE track_artist IS NULL;",
        "UPDATE songs_temp SET track_album_name = '---' WHERE track_album_name IS NULL;",
    ],
    "rename columns": [
        "ALTER TABLE songs_temp RENAME COLUMN track_id TO song_id;",
        "ALTER TABLE songs_temp RENAME COLUMN track_name TO title;",
        "ALTER TABLE songs_temp RENAME COLUMN track_artist TO artist;",
        "ALTER TABLE songs_temp RENAME COLUMN track_popularity TO song_popularity;",
        "ALTER TABLE songs_temp RENAME COLUMN track_album_id TO album_id;",
        "ALTER TABLE songs_temp RENAME COLUMN track_album_name TO album_name;",
        "ALTER TABLE songs_temp RENAME COLUMN track_album_release_date TO album_premiere;",
    ],
    "drop duplicate rows": [
        """
        DELETE FROM songs_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM songs_temp
        GROUP BY lower(title), lower(artist), lower(album_name), duration_ms
        );
        """
    ],
}
execute_commands(db_songs_temp, conn)
switch_and_drop_table("songs_temp", "songs")


# Movies table
create_table_query = """
    CREATE TABLE movies (
        id              INTEGER     PRIMARY KEY UNIQUE,
        title           VARCHAR     NOT NULL,
        premiere        DATE        NOT NULL,
        score           FLOAT,
        genres          VARCHAR     NOT NULL,
        overview        TEXT,
        crew            TEXT,
        orig_title      VARCHAR,
        orig_lang       VARCHAR,
        budget          FLOAT,
        revenue         FLOAT,
        country         VARCHAR,
        created_by      VARCHAR,
        updated_by      VARCHAR,
        UNIQUE(title, premiere)
    );
"""
create_table("movies", create_table_query, conn)

csv_file = "external_data/imdb_movies.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("movies_temp", conn, if_exists="replace")

db_movies_temp = {
    "delete rows": "DELETE FROM movies_temp WHERE genre IS NULL;",
    "add columns": [
        "ALTER TABLE movies_temp ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE movies_temp ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE movies_temp
        SET date_x =
        substr(date_x, 7,4)||'-'||
        substr(date_x, 1,2)||'-'||
        substr(date_x, 4,2);
        """,
        """
        UPDATE movies_temp
        SET crew = '---'
        WHERE crew is NULL and genre LIKE '%Animation%';
        """,
        """
        UPDATE movies_temp
        SET score = round(score/10, 2)
        WHERE score > 0;
        """,
        """
        UPDATE movies_temp
        SET created_by = "www.kaggle.com - ashpalsingh1525"
        WHERE created_by is NULL;
        """,
        "UPDATE movies_temp SET names = '---' WHERE names IS NULL;",
        "UPDATE movies_temp SET date_x = '---' WHERE date_x IS NULL;",
        "UPDATE movies_temp SET genre = '---' WHERE genre IS NULL;",
    ],
    "rename columns": [
        "ALTER TABLE movies_temp RENAME COLUMN names TO title;",
        "ALTER TABLE movies_temp RENAME COLUMN budget_x TO budget;",
        "ALTER TABLE movies_temp RENAME COLUMN genre TO genres;",
        "ALTER TABLE movies_temp RENAME COLUMN date_x TO premiere;",
    ],
    "drop columns": [
        "ALTER TABLE movies_temp DROP COLUMN status;",
    ],
    "drop duplicate rows": [
        """
        DELETE FROM  movies_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM movies_temp
        GROUP BY lower(title), premiere
        );
        """
    ],
}
execute_commands(db_movies_temp, conn)
switch_and_drop_table("movies_temp", "movies")


# Books table
create_table_query = """
    CREATE TABLE books (
        id              INTEGER     PRIMARY KEY UNIQUE,
        title           VARCHAR     NOT NULL,
        author          VARCHAR     NOT NULL,
        description     TEXT,
        genres          VARCHAR     NOT NULL,
        avg_rating      FLOAT,
        num_ratings     INTEGER,
        first_published DATE,
        created_by      VARCHAR,
        updated_by      VARCHAR,
        UNIQUE(title, author)
    );
"""
create_table("books", create_table_query, conn)

csv_file = "external_data/goodreads_data.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("books_temp", conn, if_exists="replace")

db_books_temp = {
    "drop columns #1": [
        "ALTER TABLE books_temp DROP COLUMN URL;",
        "ALTER TABLE books_temp DROP COLUMN 'Unnamed: 0';",
    ],
    "delete rows": [
        "DELETE FROM books_temp WHERE Book IS NULL;",
        "DELETE FROM books_temp WHERE Author IS NULL;",
        "DELETE FROM books_temp WHERE Genres LIKE '[]';",
    ],
    "rename columns": [
        "ALTER TABLE books_temp RENAME COLUMN Book TO title;",
        "ALTER TABLE books_temp RENAME COLUMN Author TO author;",
        "ALTER TABLE books_temp RENAME COLUMN Description TO description;",
        "ALTER TABLE books_temp RENAME COLUMN Genres TO genres;",
        "ALTER TABLE books_temp RENAME COLUMN Avg_Rating TO avg_rating;",
        "ALTER TABLE books_temp RENAME COLUMN Num_ratings TO num_ratings;",
    ],
    "add columns": [
        # "ALTER TABLE books_temp ADD COLUMN num_ratings INTEGER;",
        "ALTER TABLE books_temp ADD COLUMN first_published DATE;",
        "ALTER TABLE books_temp ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE books_temp ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE books_temp
        SET genres = replace(genres, '[', '')
        WHERE genres LIKE '[%';
        """,
        """
        UPDATE books_temp
        SET genres = replace(genres, ']', '')
        WHERE genres LIKE '%]';
        """,
        """
        UPDATE books_temp
        SET genres = replace(genres, "'", "")
        WHERE genres LIKE "%'%";
        """,
        """
        UPDATE books_temp
        SET num_ratings = replace(num_ratings, ',', '')
        WHERE num_ratings LIKE '%,%';
        """,
        """
        UPDATE books_temp
        SET created_by = "www.kaggle.com - ishikajohari"
        WHERE created_by is NULL;
        """,
        # "UPDATE books_temp SET num_ratings = Num_ratings;",
        "UPDATE books_temp SET title = '---' WHERE title IS NULL;",
        "UPDATE books_temp SET author = '---' WHERE author IS NULL;",
        "UPDATE books_temp SET genres = '---' WHERE genres IS NULL;",
    ],
    # "drop columns #2": [
    #     "ALTER TABLE books_temp DROP COLUMN Num_Ratings;",
    # ],
    "drop duplicate rows": [
        """
        DELETE FROM  books_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM books_temp
        GROUP BY lower(title), lower(author)
        );
        """
    ],
}
execute_commands(db_books_temp, conn)
switch_and_drop_table("books_temp", "books")

# Closing connection to the database
conn.close()
