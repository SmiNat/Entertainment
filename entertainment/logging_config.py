import logging
import os
from logging.config import dictConfig

from entertainment.config import DevConfig, TestConfig, config
from entertainment.enums import FontBackground, FontColor, FontReset, FontType


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
        datefmt = kwargs.pop("datefmt", "%Y-%m-%d %H:%M:%S")
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
        # Making a copy of a record to prevent altering the message for other loggers
        record = logging.makeLogRecord(record.__dict__)  # noqa: E501 >> or import copy and record = copy.copy(record)

        extra_info = record.__dict__.pop("additional information", "")
        if extra_info:
            record.msg += f"\nAdditional information: {extra_info}"

        # Changing levelname color depending on logger actual level
        color = self.MAPPING.get(record.levelname, FontColor.default)
        record.levelname = f"{color}{record.levelname:<8}{FontReset.suffix}"

        # Formatting the record using desired_format
        self._style._fmt = self.desired_format
        msg = super().format(record)  # noqa: E501 >> msg = logging.Formatter.format(self, record)
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
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",  # noqa: E501 >> logging.Formatter
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                    "format": "%(asctime)s %(msecs)03d %(levelname)s %(name)s %(filename)s %(lineno)s %(correlation_id)s %(message)s",
                },
                "test": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "format": "%(asctime)s.%(msecs)03dZ - %(levelname)8s - TEST - %(name)s - %(filename)s:%(lineno)s --- [%(correlation_id)s] %(message)s",
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
                    "level": "ERROR",
                    "formatter": "file",
                    "filename": "logs_error.log",
                    "filters": ["correlation_id"],
                    "encoding": "utf-8",
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
                    "encoding": "utf-8",
                },
                "tests": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "test",
                    "filename": os.path.join(
                        os.path.dirname(__file__), "tests", "logs_test.log"
                    ),
                    "mode": "a",
                    "maxBytes": 1024 * 256,  # 0.25MB
                    "backupCount": 1,
                    "filters": ["correlation_id"],
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "entertainment": {
                    "handlers": [
                        "console_entertainment",
                        "tests" if isinstance(config, TestConfig) else "rotating",
                        "fixed",
                    ],
                    "level": "DEBUG"
                    if isinstance(config, (DevConfig, TestConfig))
                    else "INFO",
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
