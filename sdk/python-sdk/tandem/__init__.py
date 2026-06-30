"""
Tandem Python SDK
=================

Lightweight annotation layer for marking functions as distributable
Tandem tasks. The SDK does NOT compile or execute code itself — it only:

  - validates split-independence of decorated functions (static analysis)
  - tracks immutable globals
  - batches/chunks calls according to the declared protocol
  - dispatches batched calls to a pluggable executor (a stand-in for the
    real Tandem node-routing backend, which does not exist yet)

See README.md for full documentation and examples.
"""

from tandem.errors import TandemValidationError, TandemRuntimeError
from tandem.immutable import immutable
from tandem.compute import compute
from tandem.split import split
from tandem.executor import (
    Executor,
    LocalExecutor,
    set_default_executor,
    get_default_executor,
)

__all__ = [
    "immutable",
    "compute",
    "split",
    "Executor",
    "LocalExecutor",
    "set_default_executor",
    "get_default_executor",
    "TandemValidationError",
    "TandemRuntimeError",
]

__version__ = "0.1.0"
