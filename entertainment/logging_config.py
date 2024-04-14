from logging.config import dictConfig

from entertainment.config import DevConfig, config


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "format": "%(asctime)s - %(levelname)8s - %(name)s >>> %(filename)s:%(lineno)s - %(message)s",
                },
                "file": {
                    "class": "logging.Formatter",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "format": "%(asctime)s - %(levelname)8s - %(filename)s:%(lineno)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "console",
                },
                "fixed": {
                    "class": "logging.FileHandler",
                    "level": "WARNING",
                    "formatter": "file",
                    "filename": "logs_fixed.log",
                },
                "floating": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "file",
                    "filename": "logs_floating.log",
                    "mode": "a",
                    "maxBytes": 2000,
                    "backupCount": 5,
                },
            },
            "loggers": {
                "entertainment": {
                    "handlers": ["default", "fixed", "floating"],
                    "level": "DEBUG" if isinstance(config, DevConfig) else "INFO",
                    "propagade": False,
                }
            },
        }
    )
