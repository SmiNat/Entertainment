class DatabaseError(Exception):
    """Exception raised for incorrect data input into the database."""

    def __init__(self, msg: str) -> None:
        self.message = str(msg.replace("sqlite3.IntegrityError", "DatabaseError"))

    def __str__(self) -> str:
        return str(self.message)


class DatabaseNotEmptyError(Exception):
    """Exception raised when the database table is not empty."""
