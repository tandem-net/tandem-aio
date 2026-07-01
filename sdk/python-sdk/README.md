# Tandem Python SDK

The Tandem Python SDK provides marker decorators and helper types for defining Tandem-discoverable tasks in Python.

## Install locally

From another project, install it directly from this repository path:

```bash
pip install /absolute/path/to/tandem-aio/sdk/python-sdk
```

For editable development:

```bash
pip install -e /absolute/path/to/tandem-aio/sdk/python-sdk
```

## Import

```python
import tandem
from tandem import Immutable, compute, split
```

## Notes

This package is the pure-Python SDK marker layer. It does not compile or execute tasks remotely by itself.
