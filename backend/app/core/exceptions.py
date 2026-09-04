import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error carrying a stable machine-readable error code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__("NOT_FOUND", message, status.HTTP_404_NOT_FOUND, details)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action"):
        super().__init__("PERMISSION_DENIED", message, status.HTTP_403_FORBIDDEN)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists", details: dict | None = None):
        super().__init__("CONFLICT", message, status.HTTP_409_CONFLICT, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__("UNAUTHORIZED", message, status.HTTP_401_UNAUTHORIZED)


class RateLimitedError(AppError):
    def __init__(self, message: str = "Too many requests"):
        super().__init__("RATE_LIMITED", message, status.HTTP_429_TOO_MANY_REQUESTS)


def _error_body(code: str, message: str, details: dict | None, request_id: str) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details or {}},
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        # Pydantic's exc.errors() can embed the raw exception object (e.g. under "ctx") when a
        # custom @field_validator raises a plain ValueError, which plain json.dumps can't
        # serialize — jsonable_encoder degrades anything non-serializable to a safe string.
        # "input" is dropped outright: it echoes back the submitted field value verbatim,
        # which could be a password on a validation failure.
        errors = jsonable_encoder(
            [{k: v for k, v in err.items() if k != "input"} for err in exc.errors()]
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "VALIDATION_ERROR",
                "The request contains invalid data",
                {"errors": errors},
                request_id,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body("HTTP_ERROR", str(exc.detail), None, request_id),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("INTERNAL_ERROR", "An unexpected error occurred", None, request_id),
        )
