import logging


def setup_entertainment_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            # logging.FileHandler("entertainment.log"),
            logging.StreamHandler()
        ],
    )


def setup_app_logging():
    db_logger = logging.getLogger("app")
    db_logger.setLevel(logging.INFO)


def setup_db_logging():
    db_logger = logging.getLogger("db")
    db_logger.setLevel(logging.DEBUG)


def setup_test_logging():
    test_logger = logging.getLogger("tests")
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s"
    )
    file_handler = logging.FileHandler("tests.log")
    file_handler.setFormatter(file_formatter)
    test_logger.addHandler(file_handler)


setup_entertainment_logging()
setup_app_logging()
setup_db_logging()
setup_test_logging()


app_logger = logging.getLogger("app")
db_logger = logging.getLogger("db")
test_logger = logging.getLogger("tests")
