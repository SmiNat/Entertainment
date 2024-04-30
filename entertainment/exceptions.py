from fastapi import HTTPException, status


class DatabaseError(Exception):
    """Exception raised for incorrect data input into the database."""

    def __init__(self, msg: str) -> None:
        self.message = str(msg.replace("sqlite3.IntegrityError", "DatabaseError"))

    def __str__(self) -> str:
        return str(self.message)


class DatabaseNotEmptyError(Exception):
    """Exception raised when the database table is not empty."""


class CredentialsException(HTTPException):
    """Exception raised with invalid authorization."""

    def __init__(
        self,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        detail: str | None = "Could not validate credentials",
        headers: dict[str, str] | None = {"WWW-Authenticate": "Bearer"},
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
