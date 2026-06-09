// main.rs
// entrypoint, initializes the client with constants

mod client;
mod network;
mod run;

const SERVER_ADDR: &str = "localhost:6767";
const PING_INTERVAL_SECS: u64 = 5;
const BUFFER_SIZE: usize = 8192;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting Tandem Client...");
    println!("Connecting to server at {}", SERVER_ADDR);
    
    let client = client::TandemClient::new(SERVER_ADDR.to_string());
    // client.connect().await?;
    
    Ok(())
}