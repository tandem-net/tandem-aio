use futures::future::BoxFuture;
use reqwest::{Client, Error};
use serde::Serialize;

use crate::measure;

// Internet slop
pub fn download_task(client: Client, url: impl Into<String>) -> BoxFuture<'static, Result<(), Error>> {
    let url = url.into();

    Box::pin(async move {
        let (bytes, duration) = measure::measure_download(client, &url).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);
        println!("downloaded {:.2} MB in {:.2}s ({:.2} MB/s)", mb, duration, mb / duration);
        Ok(())
    })
}

pub fn upload_task(client: Client, url: impl Into<String>, bytes: usize) -> BoxFuture<'static, Result<(), Error>> {
    let url = url.into();

    Box::pin(async move {
        let duration = measure::measure_upload(client, &url, bytes, 65536).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);

        println!("uploaded {:.2} MB in {:.2}s ({:.2} MB/s", mb, duration, mb / duration);
        Ok(())
    })
}

// Registering

fn save_node_id(node_id: &str) -> Result<(), Error> {
    std::fs::write("node_id.txt", node_id).map_err(|e| Error::from(e))
}

pub fn register<T> (client: Client, url: impl Into<String>, data: T) -> BoxFuture<'static, Result<(), Error>>
where T: Serialize + Send + 'static {
    let url = url.into();

    Box::pin(async move {
        let response = client.post(&url)
            .json(&data)
            .send()
            .await?;
        
        let node_id = response.text().await?;
        save_node_id(&node_id)?;
        
        Ok(())
    })
}