// run.rs
// Executes cloudpickle-serialized Python functions received from the server.
use bytes::Bytes;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyTuple};

/// Runs a Python function against multiple argument sets, returning serialized results.
///
/// `func_obj` — cloudpickle-serialized Python function, shared across all tasks
/// `args`     — each element is a cloudpickle-serialized tuple of args for one call
///
/// Python equivalent:
///   results = [execute_python_task(func_obj, task_args) for task_args in args]
pub async fn execute_python_tasks(func_obj: Bytes, args: Vec<Bytes>) -> Vec<Bytes> {
    let mut results = Vec::new();
    for task_args in args {
        // result = execute_python_task(func_obj, task_args)
        match execute_python_task(func_obj.clone(), task_args).await {
            Ok(result) => results.push(result),
            Err(e) => {
                // except Exception as e: print(f"Task execution failed: {e}")
                eprintln!("Task execution failed: {}", e);
                results.push(Bytes::new()); // results.append(b"")
            }
        }
    }
    results
}

/// Deserializes a Python function and its args, calls it, and returns the serialized result.
///
/// `func_obj` — cloudpickle-serialized callable
/// `args`     — cloudpickle-serialized tuple, unpacked as positional args: func(*args)
///
/// Python equivalent:
///   func = cloudpickle.loads(func_obj)
///   result = func(*cloudpickle.loads(args))
///   return cloudpickle.dumps(result)
pub async fn execute_python_task(func_obj: Bytes, args: Bytes) -> PyResult<Bytes> {
    Python::attach(|py| {
        let cloudpickle = py.import("cloudpickle")?;

        // func = cloudpickle.loads(func_obj)
        let func = cloudpickle.call_method1("loads", (PyBytes::new(py, &func_obj),))?;

        // args = cloudpickle.loads(args)
        // args must be a tuple on the Python side: cloudpickle.dumps((arg1, arg2, ...))
        let args_tuple = cloudpickle
            .call_method1("loads", (PyBytes::new(py, &args),))?
            .cast_into::<PyTuple>()?;

        // result = func(*args)
        let result = func.call1(&args_tuple)?;

        // return cloudpickle.dumps(result)
        cloudpickle
            .call_method1("dumps", (result,))?
            .extract::<Vec<u8>>()
            .map(Bytes::from)
    })
}