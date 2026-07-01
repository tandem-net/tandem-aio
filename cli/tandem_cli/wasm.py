from __future__ import annotations

import hashlib
import inspect
import json
from typing import Any


def _encode_u32(value: int) -> bytes:
    if value < 0:
        raise ValueError("WebAssembly integers must be non-negative.")

    encoded = bytearray()
    remaining = value

    while True:
        byte = remaining & 0x7F
        remaining >>= 7
        if remaining:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _encode_name(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return _encode_u32(len(encoded)) + encoded


def _section(section_id: int, payload: bytes) -> bytes:
    return bytes([section_id]) + _encode_u32(len(payload)) + payload


def _custom_section(name: str, payload: bytes) -> bytes:
    return _section(0, _encode_name(name) + payload)


def _type_section() -> bytes:
    payload = bytearray()
    payload.extend(_encode_u32(1))
    payload.append(0x60)  # function type marker
    payload.extend(_encode_u32(0))
    payload.extend(_encode_u32(0))
    return _section(1, bytes(payload))


def _function_section() -> bytes:
    payload = bytearray()
    payload.extend(_encode_u32(1))
    payload.extend(_encode_u32(0))
    return _section(3, bytes(payload))


def _export_section() -> bytes:
    export_name = "tandem_entry"
    payload = bytearray()
    payload.extend(_encode_u32(1))
    payload.extend(_encode_name(export_name))
    payload.append(0x00)  # function export kind
    payload.extend(_encode_u32(0))
    return _section(7, bytes(payload))


def _code_section() -> bytes:
    function_body = b"\x00\x0b"  # no locals, end
    payload = bytearray()
    payload.extend(_encode_u32(1))
    payload.extend(_encode_u32(len(function_body)))
    payload.extend(function_body)
    return _section(10, bytes(payload))


def build_placeholder_wasm(
    task: Any,
    manifest_entry: dict[str, Any],
    *,
    sdk_info: dict[str, Any] | None = None,
) -> bytes:
    """Create a minimal valid WASM module annotated with Tandem build metadata.

    This is intentionally a scaffold artifact. It produces a real `.wasm` binary
    with custom sections carrying the task metadata and source, while the full
    Python-to-WASM lowering backend is still under construction.
    """

    task_function = getattr(task, "function", task)

    try:
        source = inspect.getsource(task_function)
    except (OSError, TypeError):
        source = ""

    compiler_metadata = {
        "compiler": "tandem-cli",
        "backend": "python-placeholder",
        "sdk": dict(sdk_info or {}),
        "task": manifest_entry,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }

    wasm = bytearray(b"\x00asm\x01\x00\x00\x00")
    wasm.extend(
        _custom_section(
            "tandem.task",
            json.dumps(compiler_metadata, sort_keys=True).encode("utf-8"),
        )
    )

    if source:
        wasm.extend(_custom_section("tandem.source", source.encode("utf-8")))

    wasm.extend(_type_section())
    wasm.extend(_function_section())
    wasm.extend(_export_section())
    wasm.extend(_code_section())
    return bytes(wasm)
