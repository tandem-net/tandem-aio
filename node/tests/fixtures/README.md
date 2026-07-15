# Executor test fixtures

These `.wasm` files are tiny prebuilt binaries used by the executor unit tests
in `node/src/executor.rs`. They both come from the same little program that
reads all of stdin and writes it straight back to stdout:

```rust
use std::io::{Read, Write};

fn main() {
    let mut input = Vec::new();
    std::io::stdin().read_to_end(&mut input).expect("read stdin");
    std::io::stdout().write_all(&input).expect("write stdout");
}
```

- `echo_module.wasm` — built with `cargo build --release --target wasm32-wasip1`
  (a classic core module, the format the old py2wasm path produced).
- `echo_component.wasm` — built with `cargo build --release --target wasm32-wasip2`
  (a WASM component, the format the new compile engine emits).

They're checked in so the tests stay fast and hermetic. If you ever need to
regenerate them, build that program for both targets and copy the outputs here.
