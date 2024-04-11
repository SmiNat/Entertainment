# NOTE: ALL DATABASES ARE FROM KAGGLE.COM

import sqlite3

import chardet
import pandas as pd

from logger import db_logger

pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 15)


def execute_commands(commands: dict[str:str], connection: sqlite3.Connection) -> None:
    """Execute commands on SQLite database on already established connection.
    Note: does not open or close connection to the database, just uses the existing one.
    Args:
        commands (dict): dictionary of command names (keys) and SQL
            command statement (values).
        connection (sqlite3.Connection): already established connection to
            SQLite database.
    """
    for command in commands.values():
        if isinstance(command, list):
            for single_command in command:
                connection.execute(single_command)
        else:
            connection.execute(command)
    connection.commit()


def switch_and_drop_table(table_from: str, table_to: str):
    copy_db = f"INSERT INTO {table_to} SELECT * FROM {table_from};"
    conn.execute(copy_db)
    conn.commit()

    drop_db = f"DROP TABLE IF EXISTS {table_from};"
    conn.execute(drop_db)
    conn.commit()


# Opening connection to a database
conn = sqlite3.connect("entertainment.db")
cursor = conn.cursor()


# Database content

# Games table
create_table = """
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
conn.execute(create_table)
conn.commit()

csv_file = "data/games_data.csv"
with open(csv_file, "rb") as raw_data:
    result = chardet.detect(raw_data.read(100000))
db_logger.info("#️⃣  File 'games_data.csv' encoding: %s." % result)
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
        "UPDATE games_temp SET title = '---' WHERE title IS NULL;",
        "UPDATE games_temp SET release_date = '---' WHERE release_date IS NULL;",
        "UPDATE games_temp SET developer = '---' WHERE developer IS NULL;",
        "UPDATE games_temp SET genres = '---' WHERE genres IS NULL;",
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
        GROUP BY title, premiere, developer
        );
        """
    ],
}
execute_commands(db_games_temp, conn)
switch_and_drop_table("games_temp", "games")

# Songs table
create_table = """
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
    UNIQUE(title, artist, album_name)
);
"""
conn.execute(create_table)
conn.commit()

csv_file = "data/spotify_songs.csv"
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
        DELETE FROM  songs_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM songs_temp
        GROUP BY title, artist, album_name
        );
        """
    ],
}
execute_commands(db_songs_temp, conn)
switch_and_drop_table("songs_temp", "songs")

# Movies table
create_table = """
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
conn.execute(create_table)
conn.commit()

csv_file = "data/imdb_movies.csv"
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
        "UPDATE movies_temp SET orig_lang = trim(orig_lang);",
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
        DELETE FROM movies_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM movies_temp
        GROUP BY title, premiere
        );
        """
    ],
}
execute_commands(db_movies_temp, conn)
switch_and_drop_table("movies_temp", "movies")


# Books table
create_table = """
CREATE TABLE books (
    id              INTEGER     PRIMARY KEY UNIQUE,
    title           VARCHAR     NOT NULL,
    author          VARCHAR     NOT NULL,
    description     TEXT,
    genres          VARCHAR     NOT NULL,
    avg_rating      FLOAT,
    rating_reviews  INTEGER,
    created_by      VARCHAR,
    updated_by      VARCHAR,
    UNIQUE(title, author)
);
"""
conn.execute(create_table)
conn.commit()


csv_file = "data/goodreads_data.csv"
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
    ],
    "add columns": [
        "ALTER TABLE books_temp ADD COLUMN rating_reviews INTEGER;",
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
        SET Num_Ratings = replace(Num_Ratings, ',', '')
        WHERE Num_Ratings LIKE '%,%';
        """,
        """
        UPDATE books_temp
        SET created_by = "www.kaggle.com - ishikajohari"
        WHERE created_by is NULL;
        """,
        "UPDATE books_temp SET rating_reviews = Num_ratings;",
        "UPDATE books_temp SET title = '---' WHERE title IS NULL;",
        "UPDATE books_temp SET author = '---' WHERE author IS NULL;",
        "UPDATE books_temp SET genres = '---' WHERE genres IS NULL;",
    ],
    "drop columns #2": [
        "ALTER TABLE books_temp DROP COLUMN Num_Ratings;",
    ],
    "drop duplicate rows": [
        """
        DELETE FROM  books_temp
        WHERE rowid NOT IN
        (
        SELECT min(rowid)
        FROM books_temp
        GROUP BY title, author
        );
        """
    ],
}
execute_commands(db_books_temp, conn)
switch_and_drop_table("books_temp", "books")

# Closing connection to the database
conn.close()
