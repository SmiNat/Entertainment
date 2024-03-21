import logging

def setup_app_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        handlers=[
            # logging.FileHandler("app.log"),
            logging.StreamHandler()
        ],
    )

def setup_db_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        handlers=[
            # logging.FileHandler("db.log"),
            logging.StreamHandler()
        ],
    )

def setup_test_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        handlers=[
            logging.FileHandler("test.log"),
            logging.StreamHandler()
        ],
    )

setup_app_logging()
setup_db_logging()
setup_test_logging()


app_logger = logging.getLogger("app")
db_logger = logging.getLogger("db")
test_logger = logging.getLogger("tests")