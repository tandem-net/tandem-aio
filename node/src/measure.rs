use reqwest::{Client, Error};
use futures_util::StreamExt;
use std::time::Instant;

pub async fn measure_download(client: Client, url: &str) -> Result<(u64, f64), Error> {
    let start_time = Instant::now();

    let response = client.get(url)
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(format!("Error: {}", response.status()))
    }

    let mut download: u64 = 0;
    let mut stream = response.bytes_stream();

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result?;
        download += chunk.len as u64;
    }

    let elapsed = start_time.elapsed();
    let duration = elapsed.as_secs_f64();

    if duration > 0.0 {
        let mb = download as f64 / (1024.0 * 1024.0);
        let speed_mb = mb / duration;
    }

    Ok((total, dur))

}

async fn measure_upload(client: Client, url: &str, total_bytes: usize, chunk_size: usize) -> Result<f64, Error> {
    let mb = 1024 * 1024;
    let data = vec![0u8; 50 * mb];
    let body = Body::from(data);

    let start = Instant::now();

    let response = client
        .post(url)
        .body(body)
        .header("Content-Type", "application/octet-stream")
        .send()
        .await?;

    if response.status().is_success() {
        let json_response: serde_json::Value = response.json().await?;
        println!("Server Response: {:?}", json_response);
    } else {
        println!("Upload failed with status: {}", response.status());
    }

    let elapsed = start.elapsed().as_secs_f64();

    Ok((elapsed))
}
