"""Exception types raised by the Tandem SDK."""


class TandemError(Exception):
    """Base class for all Tandem SDK errors."""


class TandemValidationError(TandemError):
    """
    Raised when a function fails the split-independence check.

    This mirrors what the real Tandem CLI will raise at build/compile
    time. In the SDK (no compiler yet), this is raised eagerly at
    decoration time so violations are caught as early as possible.
    """


class TandemRuntimeError(TandemError):
    """Raised for errors that occur during dispatch/execution of a task."""
