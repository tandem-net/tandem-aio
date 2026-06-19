mod tasks;
mod measure;

use reqwest::Client;

#[tokio::main]
async fn main() {
    let client = Client::new();
    let download = "http://127.0.0.1:6767/nodes/download";
    let upload = "http://127.0.0.1:6767/nodes/upload";
    
    match tasks::download_task(client.clone(), download).await {
        Ok(()) => println!("Downloaded successfully!"),
        Err(e) => println!("Error: {}", e), // wsg shagmar
    }

    match tasks::upload_task(client.clone(), upload, 65564).await {
        Ok(()) => println!("Uploaded successfully!"),
        Err(e) => println!("Error: {}", e),
    }
}