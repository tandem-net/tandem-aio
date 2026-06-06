// serialization.rs
// handles serialization and deserialization of Python objects

pub fn deserialize(data: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
    Ok(data.to_vec())
}

pub fn serialize(data: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
    Ok(data.to_vec())
}