// serialize.rs
// handles serialization and deserialization of Python objects using cloudpickle

// Python:
//   def serialize(obj) -> bytes:
//       return cloudpickle.dumps(obj)

pub async fn serialize(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    let cloudpickle = py.import("cloudpickle")?;
    let serialized = cloudpickle.call_method1("dumps", (obj,))?;
    let bytes: Vec<u8> = serialized.extract()?;
    Ok(bytes)
}

// Python:
//   def deserialize(data: bytes) -> object:
//       return cloudpickle.loads(data)

pub async fn deserialize(py: Python<'_>, data: Vec<u8>) -> PyResult<Bound<'_, PyAny>> {
    let cloudpickle = py.import("cloudpickle")?;
    let bytes = PyBytes::new(py, &data);
    let obj = cloudpickle.call_method1("loads", (bytes,))?;
    Ok(obj)
}