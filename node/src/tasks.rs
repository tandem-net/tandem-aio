use std::env::VarError::NotUnicode;

use futures::future::BoxFuture;
use reqwest::{Client, Error};
use serde::Serialize;
use serde_json::json;

use crate::measure;

#[derive(Serialize, Clone, Debug)]
pub struct Metrics {
    pub latency: f32,
    pub download: f32,
    pub upload: f32,
}

// Internet slop
pub fn download_task(client: Client, url: impl Into<String>) -> BoxFuture<'static, Result<f32, Error>> {
    let url = url.into();

    Box::pin(async move {
        let (bytes, duration) = measure::measure_download(client, &url).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);
        let speed = (mb / duration) as f32;
        
        println!("downloaded {:.2} MB in {:.2}s ({:.2} MB/s)", mb, duration, speed);

        Ok(speed)
    })
}

pub fn upload_task(client: Client, url: impl Into<String>, bytes: usize) -> BoxFuture<'static, Result<f32, Error>> {
    let url = url.into();

    Box::pin(async move {
        let duration = measure::measure_upload(client, &url, bytes, 65536).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);
        let speed = (mb / duration) as f32;
        
        println!("uploaded {:.2} MB in {:.2}s ({:.2} MB/s", mb, duration, speed);

        Ok(speed)
    })
}

// Node ID
fn save_node_id(node_id: &str) -> Result<(), Error> {
    std::fs::write("node_id.txt", node_id).map_err(|_| {
        Client::new().get("").build().unwrap_err()
    })
}

fn load_node_id() -> Result<String, Error> {
    std::fs::read_to_string("node_id.txt").map_err(|_| {
        Client::new().get("").build().unwrap_err()
    })
}

pub fn register<T> (client: Client, url: impl Into<String>, data: T) -> BoxFuture<'static, Result<(), Error>>
where T: Serialize + Send + 'static {
    let url = url.into();

    Box::pin(async move {
        let _response = client.post(&url)
            .json(&data)
            .send()
            .await?;
        
        let json_res: serde_json::Value = _response.json().await?;
        if let Some(node_id) = json_res.get("node_id").and_then(|v| v.as_str()) {
            save_node_id(node_id)?;
        }
        
        Ok(())
    })
}

pub fn ping<T> (client: Client, url: impl Into<String>, data: T) -> BoxFuture<'static, Result<(), Error>>
where T: Serialize + Send + 'static {
    let url = url.into();

    let node_id = load_node_id().ok();
    let mut json_data = serde_json::to_value(data).unwrap_or_else(|_| json!({}));

    if let Some(id) = node_id {
        if let Some(obj) = json_data.as_object_mut() {
            obj.insert(String::from("node_id"), json!(id));
        }
    }

    Box::pin(async move {
        let _response = client.post(&url)
            .json(&json_data)
            .send()
            .await?;
        
        Ok(())
    })
}

pub fn health<T> (client: Client, url: impl Into<String>, data: T) -> BoxFuture<'static, Result<(), Error>>
where T: Serialize + Send + 'static {
    let url = url.into();

    let node_id = load_node_id().ok();
    let mut json_data = serde_json::to_value(data).unwrap_or_else(|_| json!({}));

    if let Some(id) = node_id {
        if let Some(obj) = json_data.as_object_mut() {
            obj.insert(String::from("node_id"), json!(id));
        }
    }

    
    Box::pin(async move {
        let response = client.post(&url)
            .json(&json_data)
            .send()
            .await?;
        
        response.error_for_status()?;
        
        Ok(())
    })
}