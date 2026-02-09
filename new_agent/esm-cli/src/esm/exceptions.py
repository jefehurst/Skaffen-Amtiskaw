"""Custom exceptions for ESM CLI."""


class ESMError(Exception):
    """Base exception for ESM errors."""

    pass


class AuthenticationError(ESMError):
    """Failed to authenticate with ESM."""

    pass


class SessionExpiredError(ESMError):
    """Session has expired and needs re-authentication."""

    pass


class PermissionDeniedError(ESMError):
    """User lacks permission for the requested operation."""

    pass


class ResourceNotFoundError(ESMError):
    """Requested resource does not exist."""

    pass


class ValidationError(ESMError):
    """Response validation failed (unexpected content)."""

    pass


class PasswordChangeRequiredError(AuthenticationError):
    """User must change password before continuing."""

    pass
