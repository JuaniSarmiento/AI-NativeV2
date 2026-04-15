from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-layer exceptions.

    These are raised by services and converted to HTTPException
    at the router boundary — never raised from route handlers directly.
    """

    default_message: str = "An unexpected domain error occurred."
    default_code: str = "DOMAIN_ERROR"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


class NotFoundError(DomainError):
    """Resource does not exist or is not accessible to the caller."""

    default_message = "The requested resource was not found."
    default_code = "NOT_FOUND"

    def __init__(
        self,
        resource: str | None = None,
        identifier: str | int | None = None,
        message: str | None = None,
        code: str | None = None,
    ) -> None:
        if message is None and resource is not None:
            id_part = f" with id '{identifier}'" if identifier is not None else ""
            message = f"{resource}{id_part} was not found."
        super().__init__(message=message, code=code)


class ValidationError(DomainError):
    """Input fails domain-level validation (beyond Pydantic schema checks).

    Use `field` to pinpoint the offending attribute so the router can
    surface it in the structured errors array.
    """

    default_message = "Validation failed."
    default_code = "VALIDATION_ERROR"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        field: str | None = None,
    ) -> None:
        super().__init__(message=message, code=code)
        self.field = field


class AuthorizationError(DomainError):
    """Caller is authenticated but lacks permission for the requested action."""

    default_message = "You do not have permission to perform this action."
    default_code = "FORBIDDEN"


class AuthenticationError(DomainError):
    """Caller is not authenticated or credentials are invalid/expired."""

    default_message = "Authentication is required."
    default_code = "UNAUTHORIZED"


class ConflictError(DomainError):
    """Operation cannot proceed due to a conflicting state (e.g. duplicate key)."""

    default_message = "The request conflicts with the current state of the resource."
    default_code = "CONFLICT"
