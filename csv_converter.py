import sqlite3

import chardet
import pandas as pd

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
# with open(csv_file, 'rb') as rawdata:
#     result = chardet.detect(rawdata.read(100000))
# print(result)
df = pd.read_csv(csv_file, encoding="Windows-1252", low_memory=False)
df.columns = df.columns.str.strip()
df.to_sql("games", conn, if_exists="replace")

db_games = {
    "rename columns": [
        "ALTER TABLE games RENAME COLUMN multiplayer_or_singleplayer TO game_type;",
        "ALTER TABLE games RENAME COLUMN dc_price TO price_discounted;",
    ],
    "drop column": [
        "ALTER TABLE games DROP COLUMN id;",
        "ALTER TABLE games DROP COLUMN win_support;",
        "ALTER TABLE games DROP COLUMN mac_support;",
        "ALTER TABLE games DROP COLUMN lin_support;",
    ],
    "delete rows": [
        "DELETE FROM games WHERE overall_review IS NULL AND detailed_review IS NULL;",
        """DELETE FROM games WHERE overall_review LIKE "1%" OR overall_review == "Free to play";"""
    ]
}
execute_commands(db_games, conn)

# Songs table
csv_file = "data/spotify_playlist_2010to2022.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("songs", conn, if_exists="replace")

db_songs = {
    "alter_column_genre": [
        """UPDATE songs
        SET artist_genres = replace(artist_genres, '[', '')
        WHERE artist_genres LIKE '[%';""",
        """UPDATE songs
        SET artist_genres = replace(artist_genres, ']', '')
        WHERE artist_genres LIKE '%]';""",
    ],
    "drop_columns": [
        "ALTER TABLE songs DROP COLUMN playlist_url;",
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
        "ALTER TABLE songs DROP COLUMN time_signature;",
    ],
}
execute_commands(db_songs, conn)

# Movies table
csv_file = "data/imdb_movies.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("movies", conn, if_exists="replace")

db_movies = {
    "drop_columns": "ALTER TABLE movies DROP COLUMN status;",
    "alter_column_date": """UPDATE movies
        SET date_x =
        substr(date_x, 7,4)||'-'||
        substr(date_x, 1,2)||'-'||
        substr(date_x, 4,2);""",
    "alter_column_crew": """UPDATE movies
        SET crew = '---'
        WHERE crew is NULL and genre LIKE '%Animation%';""",
    "rename_columns": [
        "ALTER TABLE movies RENAME COLUMN names TO title;",
        "ALTER TABLE movies RENAME COLUMN date_x TO premiere;",
        "ALTER TABLE movies RENAME COLUMN budget_x TO budget;",
    ],
}
execute_commands(db_movies, conn)

# Books table
csv_file = "data/goodreads_data.csv"
df = pd.read_csv(csv_file)
df.columns = df.columns.str.strip()
df.to_sql("books", conn, if_exists="replace")

db_books = {
    "drop_columns": [
        "ALTER TABLE books DROP COLUMN URL;",
        "ALTER TABLE books DROP COLUMN 'Unnamed: 0';",
    ],
    "alter_column_genres": [
        """UPDATE books
        SET Genres = replace(Genres, '[', '')
        WHERE Genres LIKE '[%';""",
        """UPDATE books
        SET Genres = replace(Genres, ']', '')
        WHERE Genres LIKE '%]';""",
    ],
    "alter_column_rating": """UPDATE books
        SET Num_Ratings = replace(Num_Ratings, ',', '')
        WHERE Num_Ratings LIKE '%,%';""",
    "rename_column": [
        "ALTER TABLE books RENAME COLUMN Book TO book;",
        "ALTER TABLE books RENAME COLUMN Author TO author;",
        "ALTER TABLE books RENAME COLUMN Description TO description;",
        "ALTER TABLE books RENAME COLUMN Genres TO genres;",
        "ALTER TABLE books RENAME COLUMN Avg_Rating TO avg_rating;",
        "ALTER TABLE books RENAME COLUMN Num_Ratings TO num_ratings;",
    ],
}
execute_commands(db_books, conn)


# Closing connection to the database
conn.close()
