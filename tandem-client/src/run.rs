// run.rs
// runs the deserialized code and handles the execution flow

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyTuple};

pub async fn execute_python_task(
    func_obj: Vec<u8>,
    args: Vec<Vec<u8>>,
) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
    println!("Spawning dynamic Python worker execution thread...");

    let result = tokio::task::spawn_blocking(move || {
        Python::with_gil(|py| -> PyResult<Vec<u8>> {//error
            // Import cloudpickle inside Python runtime
            let cloudpickle = py.import_bound("cloudpickle")?;
            
            // Reconstruct the pickled function object
            let py_func_bytes = PyBytes::new_bound(py, &func_obj); //error
            let func = cloudpickle.call_method1("loads", (py_func_bytes,))?;
            
            // Reconstruct arguments
            let mut py_args = Vec::new();
            for arg_bytes in args {
                let py_arg_bytes = PyBytes::new_bound(py, &arg_bytes);//error
                let decoded_arg = cloudpickle.call_method1("loads", (py_arg_bytes,))?;
                py_args.push(decoded_arg);
            }
            let args_tuple = PyTuple::new_bound(py, py_args);//error
            
            // Invoke user function
            let exec_result = func.call1(args_tuple)?;
            
            // Re-pickle the output 
            let serialized_output: Bound<'_, PyBytes> = cloudpickle
                .call_method1("dumps", (exec_result,))?
                .downcast_into::<PyBytes>()?;
                
            Ok(serialized_output.as_bytes().to_vec())
        })
    }).await?;

    match result {
        Ok(bytes) => Ok(bytes),
        Err(py_err) => Err(format!("Python Script Error: {:?}", py_err).into()),
    }
}