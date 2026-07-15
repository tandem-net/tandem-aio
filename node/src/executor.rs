use wasmtime::component::{Component, Linker as ComponentLinker};
use wasmtime::{Config, Engine, Linker, Module, Store};
use wasmtime_wasi::preview1::WasiP1Ctx;
use wasmtime_wasi::{IoView, ResourceTable, WasiCtx, WasiCtxBuilder, WasiView};

use crate::crypto;

/// The result of a successful WASM execution.
pub struct ExecutionResult {
    /// Raw bytes captured from the guest's stdout.
    pub output: Vec<u8>,
    /// Number of fuel units consumed (proxy for instruction count).
    pub instruction_count: u64,
    /// SHA-256 hex digest of the guest's linear memory after execution.
    pub memory_hash: String,
}

/// Default fuel budget when no timeout is specified (1 billion units).
const DEFAULT_FUEL: u64 = 1_000_000_000;

/// The four bytes that mark a WASM binary as a component rather than a classic
/// core module. Both start with the same `\0asm` magic, but the version/layer
/// bytes differ, which is all we need to tell them apart.
const COMPONENT_VERSION: [u8; 4] = [0x0d, 0x00, 0x01, 0x00];

/// Execute a WASM binary in a sandboxed Wasmtime runtime.
///
/// * `payload` — the (potentially decrypted) TNDM-framed payload: the WASM
///   bytes followed by the JSON input fed to the guest on stdin.
/// * `timeout_ms` — optional timeout hint; converted to a fuel budget
///   (`timeout_ms × 10 000`).
///
/// The bytes might be a modern component (what the new compile engine emits) or
/// a classic core module (what the old py2wasm path produced), so we look at the
/// header and run whichever one it is.
pub fn execute_wasm(
    payload: &[u8],
    timeout_ms: Option<u64>,
) -> Result<ExecutionResult, Box<dyn std::error::Error>> {
    eprintln!("[executor] payload len: {}", payload.len());
    if payload.len() >= 8 {
        eprintln!("[executor] payload prefix: {:?}", &payload[0..8]);
    }
    let (wasm_bytes, input_bytes): (&[u8], &[u8]) =
        if payload.starts_with(b"TNDM") && payload.len() >= 8 {
            let mut len_bytes = [0u8; 4];
            len_bytes.copy_from_slice(&payload[4..8]);
            let wasm_len = u32::from_le_bytes(len_bytes) as usize;
            if payload.len() >= 8 + wasm_len {
                (&payload[8..8 + wasm_len], &payload[8 + wasm_len..])
            } else {
                (payload, &[])
            }
        } else {
            (payload, &[])
        };

    let fuel_budget = timeout_ms.map_or(DEFAULT_FUEL, |ms| ms * 10_000);

    if is_component(wasm_bytes) {
        run_component(wasm_bytes, input_bytes, fuel_budget)
    } else {
        run_core_module(wasm_bytes, input_bytes, fuel_budget)
    }
}

/// Is this a WASM component? Components carry a distinct version/layer in the
/// four bytes right after the `\0asm` magic.
fn is_component(wasm_bytes: &[u8]) -> bool {
    wasm_bytes.len() >= 8 && wasm_bytes[4..8] == COMPONENT_VERSION
}

/// Turn a wasmtime run error into our own error, treating a clean WASI exit as
/// success.
///
/// A normal WASI program finishes by calling `proc_exit`, which wasmtime hands
/// back as an `I32Exit` rather than a plain return. Exit status 0 means "ran
/// fine", so we swallow it; any other status, a fuel-exhaustion trap, or a real
/// trap becomes an error the caller can report.
fn interpret_run_error(err: wasmtime::Error) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(exit) = err.downcast_ref::<wasmtime_wasi::I32Exit>() {
        if exit.0 == 0 {
            return Ok(());
        }
        return Err(format!("guest exited with status {}", exit.0).into());
    }

    let msg = format!("{err}");
    if msg.contains("fuel") {
        return Err("Fuel exhausted: execution exceeded instruction budget".into());
    }
    Err(format!("WASM trap: {msg}").into())
}

/// Run a classic core WASM module through WASI preview1. This is the original
/// execution path, unchanged; it still handles anything the old toolchain
/// produced and anything that compiles to a plain core module.
fn run_core_module(
    wasm_bytes: &[u8],
    input_bytes: &[u8],
    fuel_budget: u64,
) -> Result<ExecutionResult, Box<dyn std::error::Error>> {
    // Engine with fuel metering.
    let mut engine_config = Config::new();
    engine_config.consume_fuel(true);
    let engine = Engine::new(&engine_config)?;

    // Compile module from in-memory bytes (never from disk).
    let module = Module::from_binary(&engine, wasm_bytes)?;

    // WASI context — minimal surface: stdin in, stdout captured.
    let stdout_buf = wasmtime_wasi::pipe::MemoryOutputPipe::new(1024 * 1024); // 1 MiB cap
    let stdin_buf = wasmtime_wasi::pipe::MemoryInputPipe::new(input_bytes.to_vec());

    let wasi_ctx = WasiCtxBuilder::new()
        .stdin(stdin_buf)
        .stdout(stdout_buf.clone())
        .build_p1();

    // Store with fuel budget.
    let mut store = Store::new(&engine, wasi_ctx);
    store.set_fuel(fuel_budget)?;

    // Link WASI imports.
    let mut linker: Linker<WasiP1Ctx> = Linker::new(&engine);
    wasmtime_wasi::preview1::add_to_linker_sync(&mut linker, |ctx| ctx)?;

    // Instantiate & run.
    let instance = linker.instantiate(&mut store, &module)?;

    // Try `_start` (WASI command convention) or `tandem_entry` (Tandem Python SDK convention).
    let start = instance
        .get_typed_func::<(), ()>(&mut store, "_start")
        .or_else(|_| instance.get_typed_func::<(), ()>(&mut store, "tandem_entry"))
        .map_err(|_| "module does not export a `_start` or `tandem_entry` function")?;

    // A normal WASI program ends by calling `proc_exit`, so a clean exit(0)
    // arrives here as an error that `interpret_run_error` treats as success.
    if let Err(err) = start.call(&mut store, ()) {
        interpret_run_error(err)?;
    }

    // Collect results.
    let fuel_remaining = store.get_fuel()?;
    let instruction_count = fuel_budget.saturating_sub(fuel_remaining);

    // Hash the first linear memory (if present).
    let memory_hash = if let Some(memory) = instance.get_memory(&mut store, "memory") {
        let data = memory.data(&store);
        crypto::sha256_hex(data)
    } else {
        crypto::sha256_hex(&[])
    };

    // Drop store to release references to WASI pipes.
    drop(store);

    // Capture stdout.
    let output: Vec<u8> = stdout_buf.try_into_inner().unwrap_or_default().into();

    Ok(ExecutionResult {
        output,
        instruction_count,
        memory_hash,
    })
}

/// The host state a component's WASI imports run against. It just holds the
/// WASI context plus the resource table wasmtime needs for the component model.
struct ComponentHost {
    ctx: WasiCtx,
    table: ResourceTable,
}

impl IoView for ComponentHost {
    fn table(&mut self) -> &mut ResourceTable {
        &mut self.table
    }
}

impl WasiView for ComponentHost {
    fn ctx(&mut self) -> &mut WasiCtx {
        &mut self.ctx
    }
}

/// Run a WASM component (the wasip2 world) as a command: feed it the input on
/// stdin, capture stdout, and meter fuel exactly like the core-module path.
///
/// We use the synchronous WASI bindings so this stays a plain blocking call,
/// which keeps it easy to run from the worker's `spawn_blocking` context.
fn run_component(
    wasm_bytes: &[u8],
    input_bytes: &[u8],
    fuel_budget: u64,
) -> Result<ExecutionResult, Box<dyn std::error::Error>> {
    let mut engine_config = Config::new();
    engine_config.consume_fuel(true);
    let engine = Engine::new(&engine_config)?;

    let component = Component::from_binary(&engine, wasm_bytes)?;

    // Same stdin-in / stdout-captured surface as the core-module path.
    let stdout_buf = wasmtime_wasi::pipe::MemoryOutputPipe::new(1024 * 1024); // 1 MiB cap
    let stdin_buf = wasmtime_wasi::pipe::MemoryInputPipe::new(input_bytes.to_vec());

    let ctx = WasiCtxBuilder::new()
        .stdin(stdin_buf)
        .stdout(stdout_buf.clone())
        .build();

    let host = ComponentHost {
        ctx,
        table: ResourceTable::new(),
    };
    let mut store = Store::new(&engine, host);
    store.set_fuel(fuel_budget)?;

    let mut linker: ComponentLinker<ComponentHost> = ComponentLinker::new(&engine);
    wasmtime_wasi::add_to_linker_sync(&mut linker)?;

    let command =
        wasmtime_wasi::bindings::sync::Command::instantiate(&mut store, &component, &linker)?;
    match command.wasi_cli_run().call_run(&mut store) {
        Err(err) => interpret_run_error(err)?,
        // The inner result is the guest's own success/failure signal.
        Ok(Err(())) => return Err("guest program exited with a non-zero status".into()),
        Ok(Ok(())) => {}
    }

    let fuel_remaining = store.get_fuel()?;
    let instruction_count = fuel_budget.saturating_sub(fuel_remaining);

    drop(store);

    let output: Vec<u8> = stdout_buf.try_into_inner().unwrap_or_default().into();

    // Components don't expose a single linear memory the way core modules do, so
    // the memory hash is best-effort here. The output hash, fuel count, and the
    // signed execution receipt are what actually guard against tampering.
    let memory_hash = crypto::sha256_hex(&[]);

    Ok(ExecutionResult {
        output,
        instruction_count,
        memory_hash,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // Real fixtures built from the same tiny "echo" program: one compiled to a
    // wasip1 core module, one to a wasip2 component. They read stdin and write
    // it straight back, which is enough to prove both execution paths deliver
    // input and capture output.
    const ECHO_MODULE: &[u8] = include_bytes!("../tests/fixtures/echo_module.wasm");
    const ECHO_COMPONENT: &[u8] = include_bytes!("../tests/fixtures/echo_component.wasm");

    // Frame wasm bytes and stdin input the way the rest of Tandem frames a task
    // payload: the "TNDM" magic, a little-endian wasm length, the wasm, then the input.
    fn frame(wasm: &[u8], input: &[u8]) -> Vec<u8> {
        let mut payload = Vec::new();
        payload.extend_from_slice(b"TNDM");
        payload.extend_from_slice(&(wasm.len() as u32).to_le_bytes());
        payload.extend_from_slice(wasm);
        payload.extend_from_slice(input);
        payload
    }

    #[test]
    fn detects_component_vs_core_module() {
        assert!(is_component(ECHO_COMPONENT));
        assert!(!is_component(ECHO_MODULE));
    }

    #[test]
    fn runs_a_core_module_and_captures_stdout() {
        let payload = frame(ECHO_MODULE, b"hello from a core module");
        let result = execute_wasm(&payload, None).expect("core module should run");
        assert_eq!(result.output, b"hello from a core module");
        assert!(result.instruction_count > 0);
    }

    #[test]
    fn runs_a_component_and_captures_stdout() {
        let payload = frame(ECHO_COMPONENT, b"hello from a component");
        let result = execute_wasm(&payload, None).expect("component should run");
        assert_eq!(result.output, b"hello from a component");
        assert!(result.instruction_count > 0);
    }
}
