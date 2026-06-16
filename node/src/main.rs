use reqwest::{Client, Error};
use serde::{Deserialize, Serialize};
use std::time::Instant;
use futures_util::StreamExt;


#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new();

    let start_time = Instant::now();

    let response = client.get("http://127.0.0.1:6767/nodes/download")
        .send()
        .await?;

    if !response.status().is_success() {
        return Err(format!("Error: {}", response.status()).into());
    }

    let mut download: u64 = 0;
    let mut stream = response.bytes_stream();

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result?;
        download += chunk.len() as u64;
    }

    let duration = start_time.elapsed();
    let duration_secs = duration.as_secs_f64();

    if duration_secs > 0.0 {
        let megabytes = download as f64 / (1024.0 * 1024.0);
        // let speed_mbi = (download as f64 * 8.0) / (1024.0 * 1024.0) / duration_secs;
        let speed_mb = megabytes / duration_secs;

        println!("Downloaded: {:.2} MB", megabytes);
        println!("Time taken: {:.2} seconds", duration_secs);
        println!("Download Speed: {:.2} MB", speed_mb);
    } else {
        println!("You are cheating, too fast to measure.");
    }

    Ok(())

}