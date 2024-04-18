from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    user = "user"


class FontColor(str, Enum):
    blue = "\033[94m"
    green = "\033[92m"
    light_blue_cyan = "\033[96m"
    purple_magneta = "\033[95m"
    red = "\033[91m"
    yellow = "\033[93m"
    white = "\033[97m"
    default = "\033[39m"


class FontBackground(str, Enum):
    black = "\033[40m"
    blue = "\033[43m"
    green = "\033[42m"
    light_blue_cyan = "\033[46m"
    purple_magneta = "\033[45m"
    red = "\033[41m"
    yellow = "\033[43m"
    white = "\033[47m"
    default = "\033[49m"


class FontType(str, Enum):
    bold = "\033[1m"
    faint = "\033[2m"
    italics = "\033[3m"
    underline = "\033[4m"
    conceal = "\033[8m"
    crossed_out = "\033[9m"
    bold_off = "\033[22m"
    default = ""


class FontReset(str, Enum):
    suffix = "\033[0m"
