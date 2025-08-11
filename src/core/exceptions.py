"""Custom exceptions for the Inventory Management Service."""

from typing import Any

from fastapi import status


class InventoryManagementError(Exception):
    """Base exception for all inventory management errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str | None = None,
        details: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or []
        self.context = context or {}


class ValidationError(InventoryManagementError):
    """Raised when request validation fails."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, **kwargs
        )


class NotFoundError(InventoryManagementError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, **kwargs)


class ConflictError(InventoryManagementError):
    """Raised when there's a conflict with the current state."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, **kwargs)


class InsufficientStockError(InventoryManagementError):
    """Raised when there's not enough stock available."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT, **kwargs)


class UnauthorizedError(InventoryManagementError):
    """Raised when authentication is required but not provided."""

    def __init__(self, message: str = "Authentication required", **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED, **kwargs)


class ForbiddenError(InventoryManagementError):
    """Raised when the user doesn't have permission."""

    def __init__(
        self, message: str = "Insufficient permissions", **kwargs: Any
    ) -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN, **kwargs)


class BadRequestError(InventoryManagementError):
    """Raised when the request is malformed or invalid."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST, **kwargs)


class ServiceUnavailableError(InventoryManagementError):
    """Raised when a dependent service is unavailable."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(
            message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, **kwargs
        )


class RateLimitError(InventoryManagementError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(
            message, status_code=status.HTTP_429_TOO_MANY_REQUESTS, **kwargs
        )


class InternalServerError(InventoryManagementError):
    """Raised for unexpected internal errors."""

    def __init__(self, message: str = "Internal server error", **kwargs: Any) -> None:
        super().__init__(
            message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, **kwargs
        )