"""Exception types raised by the Tandem SDK."""


class TandemError(Exception):
    """Base class for all Tandem SDK errors."""


class TandemValidationError(TandemError):
    """
    Raised when a function fails the split-independence check at
    decoration time.

    The SDK validates independence eagerly (at the moment @tandem.compute
    or tandem.split() is applied) so violations surface immediately --
    not at compile time or first call. The compiler re-validates with
    full symbol resolution during `tandem build`; this check catches the
    obvious cases at development time.
    """
