"""Exception types raised by the Tandem SDK."""


class TandemError(Exception):
    """Base class for all Tandem SDK errors."""


class TandemValidationError(TandemError):
    """
    Raised when a function fails the split-independence check at
    decoration time.
    """
