"""
Tandem Python SDK
=================

Marker layer for declaring Tandem tasks. The SDK:
  - marks functions as compute or split tasks via decorators
  - validates split-independence at decoration time
  - attaches metadata the compiler reads during `tandem build`

It does NOT compile, execute, batch, dispatch, or talk to any server.
"""

from tandem.errors import TandemValidationError
from tandem.immutable import Immutable
from tandem.compute import compute
from tandem.split import split

__all__ = [
    "Immutable",
    "compute",
    "split",
    "TandemValidationError",
]

__version__ = "0.1.0"
