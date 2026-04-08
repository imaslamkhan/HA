class StayEaseError(Exception):
    """Base domain exception."""


class AuthorizationError(StayEaseError):
    """Raised when role or tenancy checks fail."""


class BookingConflictError(StayEaseError):
    """Raised when overlapping inventory is detected."""
