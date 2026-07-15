# Executor test fixtures

Small prebuilt WASM binaries used by the executor unit tests in
`node/src/executor.rs`. They're checked in so the tests stay fast and hermetic.

- `echo_module.wasm` — a classic **core module** (wasip1). Built from a tiny
  Rust program that reads all of stdin and writes it back to stdout:

  ```rust
  use std::io::{Read, Write};
  fn main() {
      let mut input = Vec::new();
      std::io::stdin().read_to_end(&mut input).unwrap();
      std::io::stdout().write_all(&input).unwrap();
  }
  ```
  Built with `cargo build --release --target wasm32-wasip1`. This is the format
  the old py2wasm path produced, and the node still runs it through the
  core-module path.

- `task_run_component.wasm` — a real **component** (wasip2) that implements
  Tandem's task contract, `run: func(input: list<u8>) -> list<u8>`, as an echo.
  Built from a small `wit-bindgen` guest against `sdk/wit/task.wit`:

  ```rust
  wit_bindgen::generate!({ path: "wit", world: "task" });
  struct Component;
  impl Guest for Component {
      fn run(input: Vec<u8>) -> Vec<u8> { input }
  }
  export!(Component);
  ```
  Built with `cargo build --release --target wasm32-wasip2`. This is the shape
  the componentize-py backend emits for Python tasks, so the node runs it by
  calling the `run` export.

If you ever need to regenerate them, rebuild those programs for the matching
target and copy the outputs here.
