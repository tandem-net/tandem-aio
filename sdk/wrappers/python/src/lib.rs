//! PyO3 bridge for forwarding Python task payloads into the Tandem Rust core.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use tandem_core::TandemCoreError;

fn map_core_error(error: TandemCoreError) -> PyErr {
    match error {
        TandemCoreError::EmptyPayload => PyValueError::new_err(error.to_string()),
        TandemCoreError::InvalidEndpoint(_) => PyRuntimeError::new_err(error.to_string()),
    }
}

/// Submits serialized Python bytes to the Rust Tandem core.
#[pyfunction]
#[pyo3(text_signature = "(bytes)")]
fn submit_task_bytes(bytes: &[u8]) -> PyResult<String> {
    let task = tandem_core::submit_task_bytes(bytes).map_err(map_core_error)?;
    Ok(task.id)
}

/// Python module exported by maturin/PyO3.
#[pymodule]
fn tandem_native(_python: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(submit_task_bytes, module)?)?;
    Ok(())
}
