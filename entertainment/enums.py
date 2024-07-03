from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class TokenExp(int, Enum):
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


class FontColor(str, Enum):
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    LIGTH_BLUE_CYAN = "\033[96m"
    PURPLE_MAGNETA = "\033[95m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    WHITE = "\033[97m"
    DEFAULT = "\033[39m"


class FontBackground(str, Enum):
    BLACK = "\033[40m"
    BLUE = "\033[43m"
    GREEN = "\033[42m"
    LIGTH_BLUE_CYAN = "\033[46m"
    PURPLE_MAGNETA = "\033[45m"
    RED = "\033[41m"
    YELLOW = "\033[43m"
    WHITE = "\033[47m"
    DEFAULT = "\033[49m"


class FontType(str, Enum):
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALICS = "\033[3m"
    UNDERLINE = "\033[4m"
    CONCEAL = "\033[8m"
    CROSSED_OUT = "\033[9m"
    BOLD_OFF = "\033[22m"
    DEFAULT = ""


class FontReset(str, Enum):
    SUFFIX = "\033[0m"


class MovieGenre(str, Enum):
    ACTION = "action"
    ADVENTURE = "adventure"
    ANIMATION = "animation"
    COMEDY = "comedy"
    CRIME = "crime"
    DOCUMENTARY = "documentary"
    DRAMA = "drama"
    FAMILY = "family"
    FANTASY = "fantasy"
    HISTORY = "history"
    HORROR = "horror"
    MUSIC = "music"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    SCI_FI = "science fiction"
    THRILLER = "thriller"
    TV_MOVIE = "tv movie"
    WAR = "war"
    WESTERN = "western"


class GamesReviewOverall(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    NEGATIVE = "Negative"
    MIXED = "Mixed"
    POSITIVE = "Positive"


class GamesReviewDetailed(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    VERY_NEGATIVE = "Very Negative"
    NEGATIVE = "Negative"
    MOSTLY_NEGATIVE = "Mostly Negative"
    MIXED = "Mixed"
    MOSTLY_POSITIVE = "Mostly Positive"
    POSITIVE = "Positive"
    VERY_POSITIVE = "Very Positive"
    CRAZY_POSITIVE = "Overwhelmingly Positive"


class EntertainmentCategory(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    BOOKS = "Books"
    GAMES = "Games"
    MOVIES = "Movies"
    SONGS = "Songs"


class WishlistCategory(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    NEVER = "Black list"
    MAYBE = "Maybe someday"
    DEFINITELY = "Definitely someday"
    ASAP = "ASAP"


class MyRate(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    TRASH = "Never again"
    OMG = "Tragedy"
    NOPE = "Nope"
    HMMM = "Not bad"
    NICE = "Nice"
    AWESOME = "Awesome"
    GOLD = "Masterpiece"


class SongGenres(str, Enum):
    @classmethod
    def list_of_values(cls):
        return list(map(lambda c: c.value, cls))

    EDM = "edm"
    LATIN = "latin"
    POP = "pop"
    R_B = "r&b"
    RAP = "rap"
    ROCK = "rock"
