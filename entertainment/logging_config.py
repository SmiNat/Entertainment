import logging
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


class ColoredFormatter(logging.Formatter):
    MAPPING = {
        "DEBUG": FontColor.white,
        "INFO": FontColor.light_blue_cyan,
        "WARNING": FontColor.yellow,
        "ERROR": FontColor.red,
        "CRITICAL": FontBackground.red,
    }

    def __init__(
        self,
        custom_format=None,
        name_color=FontColor.default,
        name_font_type=FontType.default,
        message_color=FontColor.default,
        message_font_type=FontType.default,
        *args,
        **kwargs,
    ):
        datefmt = kwargs.pop("datefmt", "%Y-%m-%dT%H:%M:%S")
        logging.Formatter.__init__(self, *args, datefmt=datefmt, **kwargs)  # noqa: E501 >> super().__init__(*args, datefmt=datefmt, **kwargs)

        if not custom_format:
            self.desired_format = (
                "%(asctime)s.%(msecs)03dZ - "
                "%(levelname)-8s - "
                f"{name_color}{name_font_type}%(name)s{FontReset.suffix} - "
                "%(filename)s:%(lineno)s - %(funcName)s"
                f"{FontColor.yellow} >>> {FontReset.suffix} "
                f"[%(correlation_id)s] "
                f"{message_color}{message_font_type}%(message)s{FontReset.suffix}"
            )
        else:
            self.desired_format = custom_format

    def format(self, record):
        # Changing levelname color depending on logger actual level
        # Check if output is a terminal (console) - for some reason, without it, the file logs with formatter set on class logging.Formatter also has the following code imbedded
        if hasattr(record, "stream"):
            color = self.MAPPING.get(record.levelname, FontColor.default)
            record.levelname = f"{color}{record.levelname:<8}{FontReset.suffix}"
        # Formatting the record using desired_format
        self._style._fmt = self.desired_format
        msg = super().format(record)  # noqa: E501 >> msg = super().format(record)  msg = logging.Formatter.format(self, record)
        return msg


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
                "libraries": {
                    "()": ColoredFormatter,
                    "name_color": FontColor.green,
                    "name_font_type": FontType.faint,
                },
                "app": {
                    "()": ColoredFormatter,
                    "name_color": FontColor.green,
                    "message_color": FontColor.green,
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
                    "formatter": "libraries",
                    "filters": ["correlation_id"],
                },
                "console_entertainment": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "app",
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
