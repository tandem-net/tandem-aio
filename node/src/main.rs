mod tasks;
mod measure;

use reqwest::Client;
use tokio::time::Instant;

#[tokio::main]
async fn main() {
    let client = Client::new();
    
    let register = "http://127.0.0.1:6767/nodes/register";
    let ping = "http://127.0.0.1:6767/nodes/ping";
    let health = "http://127.0.0.1:6767/nodes/health";
    
    let download = "http://127.0.0.1:6767/nodes/download";
    let upload = "http://127.0.0.1:6767/nodes/upload";
    
    let download_speed = match tasks::download_task(client.clone(), download).await {
        Ok(speed) => {
            println!("Downloaded successfully!");
            speed
        }
        Err(e) => {
            println!("Error: {}", e);
            0.0
        }
    };

    let upload_speed = match tasks::upload_task(client.clone(), upload, 65564).await {
        Ok(speed) => {
            println!("Uploaded successfully!");
            speed
        }
        Err(e) => {
            println!("Error: {}", e);
            0.0
        }
    };

    let start = Instant::now();
    let latency = match client.get("http://127.0.0.1:6767")
        .send()
        .await {
            Ok(_) => start.elapsed().as_secs_f32() * 1000.0,
            Err(_) => 0.0,
    };

    let metrics = tasks::Metrics {
        latency,
        download: download_speed,
        upload: upload_speed,
    };

    if let Err(e) = tasks::register(client.clone(), register, metrics.clone()).await {
        println!("register failed: {}", e);
    }

    if let Err(e) = tasks::health(client.clone(), health, metrics.clone()).await {
        println!("health failed: {}", e);
    }

    if let Err(e) = tasks::ping(client.clone(), ping, metrics.clone()).await {
        println!("ping failed: {}", e);
    }
}