"""Exception types raised by the Tandem SDK."""


class TandemError(Exception):
    """Base class for all Tandem SDK errors."""


class TandemValidationError(TandemError):
    """
    Raised when a function fails the split-independence check at
    decoration time.
    """


class TandemBuildError(TandemError):
    """
    Raised when a function cannot be compiled to WASM during
    ``tandem build``.

    Attributes
    ----------
    line : int | None
        The 1-based source line number where the error was detected.
    hint : str
        A human-readable suggestion for how to fix the problem.
    """

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        hint: str = "",
    ) -> None:
        if line is not None:
            full = f"line {line}: {message}"
        else:
            full = message
        if hint:
            full = f"{full} (hint: {hint})"
        super().__init__(full)
        self.line = line
        self.hint = hint
