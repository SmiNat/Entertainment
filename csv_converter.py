import os
import sqlite3

import chardet
import pandas as pd

from logger import db_logger


pd.set_option("display.width", 300)
pd.set_option("display.max_columns", 15)


# NOTE: ALL DATABASES ARE FROM KAGGLE.COM


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


# Opening connection to a database
conn = sqlite3.connect("entertainment.db")
cursor = conn.cursor()


# Database content

# Games table
csv_file = "data/games_data.csv"
with open(csv_file, 'rb') as raw_data:
    result = chardet.detect(raw_data.read(100000))
db_logger.info("#️⃣  File 'games_data.csv' encoding: %s." %result)
df = pd.read_csv(csv_file, encoding="Windows-1252", low_memory=False)
df.columns = df.columns.str.strip()
df.to_sql("games", conn, if_exists="replace")

# Note: The PRICE is in INR - this will be converted to EUR @0.011 exchange rate

db_games = {
    "drop columns #1": [
        "ALTER TABLE games DROP COLUMN id;",
        "ALTER TABLE games DROP COLUMN win_support;",
        "ALTER TABLE games DROP COLUMN mac_support;",
        "ALTER TABLE games DROP COLUMN lin_support;",
    ],
    "delete rows": [
        """
        DELETE FROM games
        WHERE overall_review IS NULL AND detailed_review IS NULL;
        """,
        """
        DELETE FROM games
        WHERE overall_review LIKE "1%" OR overall_review == "Free to play";
        """,
        "DELETE FROM games WHERE title IS NULL;",
        "DELETE FROM games WHERE title LIKE '%???%';",
    ],
    "add columns": [
        "ALTER TABLE games ADD COLUMN premiere DATE;",
        "ALTER TABLE games ADD COLUMN price_eur REAL;",
        "ALTER TABLE games ADD COLUMN price_discounted_eur REAL;",
        "ALTER TABLE games ADD COLUMN reviews_number INTEGER;",
        "ALTER TABLE games ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE games ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        "UPDATE games SET premiere = release_date;",
        """
        UPDATE games
        SET developer = replace(developer, ';', ', ')
        WHERE developer LIKE '%;%';
        """,
        """
        UPDATE games
        SET publisher = replace(publisher, ';', ', ')
        WHERE publisher LIKE '%;%';
        """,
        """
        UPDATE games
        SET genres = replace(genres, ';', ', ')
        WHERE genres LIKE '%;%';
        """,
        """
        UPDATE games
        SET multiplayer_or_singleplayer = replace(multiplayer_or_singleplayer, ';', ', ')
        WHERE multiplayer_or_singleplayer LIKE '%;%';
        """,
        "UPDATE games SET price = replace(price, ',', '') WHERE price LIKE '%,%';",
        "UPDATE games SET price = round(price*0.011, 2) WHERE price > 0;",
        "UPDATE games SET price_eur = price;",
        """
        UPDATE games
        SET dc_price = replace(dc_price, ',', '')
        WHERE dc_price LIKE '%,%';
        """,
        "UPDATE games SET dc_price = round(dc_price*0.011, 2) WHERE dc_price > 0;",
        "UPDATE games SET price_discounted_eur = dc_price;",
        "UPDATE games SET reviews_number = reviews;",
        """
        UPDATE games
        SET created_by = "www.kaggle.com - rahuldabholkar"
        WHERE created_by is NULL;
        """,
    ],
    "rename columns": [
        "ALTER TABLE games RENAME COLUMN overall_review TO review_overall;",
        "ALTER TABLE games RENAME COLUMN detailed_review TO review_detailed;",
        "ALTER TABLE games RENAME COLUMN percent_positive TO reviews_positive;",
        "ALTER TABLE games RENAME COLUMN multiplayer_or_singleplayer TO type;",
    ],
    "drop columns #2": [
        "ALTER TABLE games DROP COLUMN release_date;",
        "ALTER TABLE games DROP COLUMN price;",
        "ALTER TABLE games DROP COLUMN dc_price;",
        "ALTER TABLE games DROP COLUMN reviews;",
    ],
}
execute_commands(db_games, conn)

# Songs table
csv_file = "data/spotify_songs.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("songs", conn, if_exists="replace")

db_songs = {
    "drop columns": [
        "ALTER TABLE songs DROP COLUMN danceability;",
        "ALTER TABLE songs DROP COLUMN energy;",
        "ALTER TABLE songs DROP COLUMN key;",
        "ALTER TABLE songs DROP COLUMN loudness;",
        "ALTER TABLE songs DROP COLUMN mode;",
        "ALTER TABLE songs DROP COLUMN speechiness;",
        "ALTER TABLE songs DROP COLUMN acousticness;",
        "ALTER TABLE songs DROP COLUMN instrumentalness;",
        "ALTER TABLE songs DROP COLUMN liveness;",
        "ALTER TABLE songs DROP COLUMN valence;",
        "ALTER TABLE songs DROP COLUMN tempo;",
    ],
    "rename columns": [
        "ALTER TABLE songs RENAME COLUMN track_id TO song_id;",
        "ALTER TABLE songs RENAME COLUMN track_name TO title;",
        "ALTER TABLE songs RENAME COLUMN track_artist TO artist;",
        "ALTER TABLE songs RENAME COLUMN track_popularity TO song_popularity;",
        "ALTER TABLE songs RENAME COLUMN track_album_id TO album_id;",
        "ALTER TABLE songs RENAME COLUMN track_album_name TO album_name;",
    ],
    "add columns": [
        "ALTER TABLE songs ADD COLUMN album_premiere DATE;",
        "ALTER TABLE songs ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE songs ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE songs
        SET album_premiere = track_album_release_date;
        """,
        """
        UPDATE songs
        SET created_by = "www.kaggle.com - joebeachcapital"
        WHERE created_by is NULL;
        """,
    ],
    "drop columns #2": [
        "ALTER TABLE songs DROP COLUMN track_album_release_date;",
    ]

}
execute_commands(db_songs, conn)

# Movies table
csv_file = "data/imdb_movies.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("movies", conn, if_exists="replace")

db_movies = {
    "delete rows": "DELETE FROM movies WHERE genre IS NULL;",
    "rename columns": [
        "ALTER TABLE movies RENAME COLUMN names TO title;",
        "ALTER TABLE movies RENAME COLUMN budget_x TO budget;",
        "ALTER TABLE movies RENAME COLUMN genre TO genres;",
    ],
    "add columns": [
        "ALTER TABLE movies ADD COLUMN premiere Date;",
        "ALTER TABLE movies ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE movies ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE movies
        SET date_x =
        substr(date_x, 7,4)||'-'||
        substr(date_x, 1,2)||'-'||
        substr(date_x, 4,2);
        """,
        "UPDATE movies SET premiere = date_x;",
        """
        UPDATE movies
        SET crew = '---'
        WHERE crew is NULL and genres LIKE '%Animation%';
        """,
        """
        UPDATE movies
        SET score = round(score/10, 2)
        WHERE score > 0;
        """,
        """
        UPDATE movies
        SET created_by = "www.kaggle.com - ashpalsingh1525"
        WHERE created_by is NULL;
        """,
    ],
    "drop columns": [
        "ALTER TABLE movies DROP COLUMN date_x;",
        "ALTER TABLE movies DROP COLUMN status;",
    ]
}
execute_commands(db_movies, conn)

# Books table
csv_file = "data/goodreads_data.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("books", conn, if_exists="replace")

db_books = {
    "drop columns #1": [
        "ALTER TABLE books DROP COLUMN URL;",
        "ALTER TABLE books DROP COLUMN 'Unnamed: 0';",
    ],
    "delete rows": [
        "DELETE FROM books WHERE Book IS NULL;",
        "DELETE FROM books WHERE Author IS NULL;",
        "DELETE FROM books WHERE Genres LIKE '[]';",
    ],
    "rename columns": [
        "ALTER TABLE books RENAME COLUMN Book TO title;",
        "ALTER TABLE books RENAME COLUMN Author TO author;",
        "ALTER TABLE books RENAME COLUMN Description TO description;",
        "ALTER TABLE books RENAME COLUMN Genres TO genres;",
        "ALTER TABLE books RENAME COLUMN Avg_Rating TO avg_rating;",
    ],
    "add columns": [
        "ALTER TABLE books ADD COLUMN rating_reviews INTEGER;",
        "ALTER TABLE books ADD COLUMN created_by VARCHAR;",
        "ALTER TABLE books ADD COLUMN updated_by VARCHAR;",
    ],
    "update columns": [
        """
        UPDATE books
        SET genres = replace(genres, '[', '')
        WHERE genres LIKE '[%';
        """,
        """
        UPDATE books
        SET genres = replace(genres, ']', '')
        WHERE genres LIKE '%]';
        """,
        """
        UPDATE books
        SET genres = replace(genres, "'", "")
        WHERE genres LIKE "%'%";
        """,
        """
        UPDATE books
        SET Num_Ratings = replace(Num_Ratings, ',', '')
        WHERE Num_Ratings LIKE '%,%';
        """,
        """
        UPDATE books
        SET created_by = "www.kaggle.com - ishikajohari"
        WHERE created_by is NULL;
        """,
        "UPDATE books SET rating_reviews = Num_ratings;",
    ],
    "drop columns #2": [
        "ALTER TABLE books DROP COLUMN Num_Ratings;",
    ],
}
execute_commands(db_books, conn)


# Closing connection to the database
conn.close()
