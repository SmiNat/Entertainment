from enum import Enum
from logging.config import dictConfig

from entertainment.config import DevConfig, config


class FontColor(str, Enum):
    blue = "\033[94m"
    green = "\033[92m"
    light_blue_cyan = "\033[96m"
    purple_magneta = "\033[95m"
    red = "\033[91m"
    yellow = "\033[93m"
    white = "\033[97m"


class FontBackground(str, Enum):
    black = "\033[40m"
    blue = "\033[43m"
    green = "\033[42m"
    light_blue_cyan = "\033[46m"
    purple = "\033[45m"
    red = "\033[41m"
    yellow = "\033[43m"
    white = "\033[47m"


class FontType(str, Enum):
    bold = "\033[1m"
    dark = "\033[2m"
    italics = "\033[3m"
    underline = "\033[4m"


class FontEnd(str, Enum):
    suffix = "\033[0m"


# MAPPING = {
#     "DEBUG": FontColor.white,
#     "INFO": FontColor.light_blue_cyan,
#     "WARNING": FontColor.yellow,
#     "ERROR": FontColor.red,
#     "CRITICAL": FontBackground.red,
# }


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 8 if isinstance(config, DevConfig) else 32,
                    "default_value": "-",
                },
            },
            "formatters": {
                "console_green": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d  %H:%M:%S",
                    "format": f"%(asctime)s.%(msecs)03dZ - %(levelname)-8s - {FontColor.green}{FontType.underline}%(name)s{FontEnd.suffix} - %(filename)s:%(lineno)s {FontColor.yellow} >>> {FontEnd.suffix} [%(correlation_id)s] %(message)s",
                },
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d  %H:%M:%S",
                    "format": f"%(asctime)s.%(msecs)03dZ - %(levelname)-8s - {FontColor.blue}%(name)s{FontEnd.suffix} - %(filename)s:%(lineno)s {FontColor.yellow} >>> {FontEnd.suffix} [%(correlation_id)s] %(message)s",
                },
                "file": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "format": "%(asctime)s - %(levelname)8s - %(name)s - %(filename)s:%(lineno)s --- [%(correlation_id)s] %(message)s",
                },
            },
            "handlers": {
                "console_libraries": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console_green",
                    "filters": ["correlation_id"],
                },
                "console_entertainment": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console",
                    "filters": ["correlation_id"],
                },
                "fixed": {
                    "class": "logging.FileHandler",
                    "level": "WARNING",
                    "formatter": "file",
                    "filename": "logs_warnings.log",
                    "filters": ["correlation_id"],
                },
                "rotating": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "file",
                    "filename": "logs_rotating.log",
                    "mode": "a",
                    "maxBytes": 1024 * 512,  # 0.5MB
                    "backupCount": 3,
                    "filters": ["correlation_id"],
                },
            },
            "loggers": {
                "entertainment": {
                    "handlers": ["console_entertainment", "fixed", "rotating"],
                    "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
                    "propagade": False,
                },
                "uvicorn": {
                    "handlers": ["console_libraries", "fixed", "rotating"],
                    "level": "INFO",
                },
                "aiosqlite": {
                    "handlers": ["console_libraries", "fixed", "rotating"],
                    "level": "WARNING",
                },
            },
        }
    )
