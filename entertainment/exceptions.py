from fastapi import HTTPException, status


class DatabaseError(Exception):
    """Exception raised for incorrect data input into the database."""

    def __init__(self, msg: str) -> None:
        self.message = str(msg.replace("sqlite3.IntegrityError", "DatabaseError"))

    def __str__(self) -> str:
        return str(self.message)


class DatabaseNotEmptyError(Exception):
    """Exception raised when the database table is not empty."""


class DatabaseIntegrityError(HTTPException):
    """Exception raised with not unique data fields."""

    DETAIL = "Record already exists in the database."

    def __init__(
        self,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail: str | None = None,
        headers: dict[str, str] | None = {"WWW-Authenticate": "Bearer"},
    ) -> None:
        self.status_code = status_code
        self.detail = (
            "Unique constraint failed: " + self.DETAIL if not detail else detail
        )
        self.headers = headers


class CredentialsException(HTTPException):
    """Exception raised with invalid authorization."""

    def __init__(
        self,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        detail: str = "Could not validate credentials.",
        headers: dict[str, str] = {"WWW-Authenticate": "Bearer"},
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


class RecordNotFoundException(HTTPException):
    """ "Exception raised if the record is not present in the database."""

    def __init__(
        self,
        status_code: int = status.HTTP_404_NOT_FOUND,
        detail: str = "The record was not found in the database.",
        extra_data: str | None = None,
        headers: dict[str, str] = {"WWW-Authenticate": "Bearer"},
    ) -> None:
        self.status_code = status_code
        if not extra_data:
            self.detail = detail
        else:
            self.detail = detail + " " + extra_data
        self.headers = headers
