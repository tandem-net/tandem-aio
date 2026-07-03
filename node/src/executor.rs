use wasmtime::{Config, Engine, Linker, Module, Store};
use wasmtime_wasi::preview1::WasiP1Ctx;
use wasmtime_wasi::WasiCtxBuilder;

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

/// Execute a WASM binary in a sandboxed Wasmtime runtime.
///
/// * `wasm_bytes` — the (potentially decrypted) WASM module bytes.
/// * `timeout_ms` — optional timeout hint; converted to a fuel budget
///                   (`timeout_ms × 10 000`).
pub fn execute_wasm(
    payload: &[u8],
    timeout_ms: Option<u64>,
) -> Result<ExecutionResult, Box<dyn std::error::Error>> {
    eprintln!("[executor] payload len: {}", payload.len());
    if payload.len() >= 8 {
        eprintln!("[executor] payload prefix: {:?}", &payload[0..8]);
    }
    let (wasm_bytes, input_bytes): (&[u8], &[u8]) = if payload.starts_with(b"TNDM") && payload.len() >= 8 {
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

    // ── Engine with fuel metering ───────────────────────────────────────
    let mut engine_config = Config::new();
    engine_config.consume_fuel(true);
    let engine = Engine::new(&engine_config)?;

    // ── Compile module from in-memory bytes (never from disk) ───────────
    let module = Module::from_binary(&engine, wasm_bytes)?;

    // ── WASI context — minimal surface: stdout capture only ─────────────
    let stdout_buf = wasmtime_wasi::pipe::MemoryOutputPipe::new(1024 * 1024); // 1 MiB cap
    let stdin_buf = wasmtime_wasi::pipe::MemoryInputPipe::new(input_bytes.to_vec());

    let wasi_ctx = WasiCtxBuilder::new()
        .stdin(stdin_buf)
        .stdout(stdout_buf.clone())
        .build_p1();

    // ── Store with fuel budget ──────────────────────────────────────────
    let fuel_budget = timeout_ms.map_or(DEFAULT_FUEL, |ms| ms * 10_000);
    let mut store = Store::new(&engine, wasi_ctx);
    store.set_fuel(fuel_budget)?;

    // ── Link WASI imports ───────────────────────────────────────────────
    let mut linker: Linker<WasiP1Ctx> = Linker::new(&engine);
    wasmtime_wasi::preview1::add_to_linker_sync(&mut linker, |ctx| ctx)?;

    // ── Instantiate & run ───────────────────────────────────────────────
    let instance = linker.instantiate(&mut store, &module)?;

    // Try `_start` (WASI command convention) or `tandem_entry` (Tandem Python SDK convention).
    let start = instance
        .get_typed_func::<(), ()>(&mut store, "_start")
        .or_else(|_| instance.get_typed_func::<(), ()>(&mut store, "tandem_entry"))
        .map_err(|_| "module does not export a `_start` or `tandem_entry` function")?;

    let run_result = start.call(&mut store, ());

    // Check for fuel exhaustion.
    if let Err(ref trap) = run_result {
        let msg = format!("{trap}");
        if msg.contains("fuel") {
            return Err(
                "Fuel exhausted: execution exceeded instruction budget".into(),
            );
        }
        // Re-surface any other trap.
        return Err(format!("WASM trap: {msg}").into());
    }
    // Propagate unexpected errors that aren't traps.
    run_result?;

    // ── Collect results ─────────────────────────────────────────────────
    let fuel_remaining = store.get_fuel()?;
    let instruction_count = fuel_budget.saturating_sub(fuel_remaining);

    // Hash the first linear memory (if present).
    let memory_hash = if let Some(memory) = instance.get_memory(&mut store, "memory") {
        let data = memory.data(&store);
        crypto::sha256_hex(data)
    } else {
        crypto::sha256_hex(&[])
    };

    // Drop store to release references to WASI pipes
    drop(store);

    // Capture stdout.
    let output: Vec<u8> = stdout_buf
        .try_into_inner()
        .unwrap_or_default()
        .into();

    Ok(ExecutionResult {
        output,
        instruction_count,
        memory_hash,
    })
}
