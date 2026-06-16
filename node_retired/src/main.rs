// main.rs
// entrypoint, initializes the client with constants

use crate::network::packets::{HeartbeatPacket, Packet, PacketType, RegisterPacket};

mod client;
mod network;

const SERVER_ADDR: &str = "127.0.0.1:6767";
// const PING_INTERVAL_SECS: u8 = 5; NOT NEEDED

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting Tandem Client...");
    println!("Connecting to server at {}", SERVER_ADDR);
    
    let mut client = client::TandemClient::new(SERVER_ADDR.to_string());
    client.connect().await;

    Ok(())
}


// async fn test() {
//     println!("Hello test world!");
//     let mut client = client::TandemClient::new(SERVER_ADDR.to_string());
//     client.connect().await;
//     if let Some(connection) = &mut client.get_connection() {
//         match connection.send_packet(Packet::new(PacketType::Heartbeat(HeartbeatPacket {
//             timestamp_unix_ms: 123125124 as u64,
//         }))).await {
//             Ok(_) => println!("Sent heartbeat packet to server."),
//             Err(e) => eprintln!("Failed to send heartbeat packet: {}", e),
//         }

//         let register_packet = Packet::new(PacketType::Register(RegisterPacket {
//             client_id: "client123".to_owned(),
//             hostname: "testmachine".to_string(),
//             cpu_cores: 4,
//             memory_bytes: 16 * 1024 * 1024 * 1024,
//             gpu_name: Some("pee".to_owned()),
//             gpu_memory_bytes: Some(8 * 1024 * 1024 * 1024),
//             python_version: "realpyversion".to_string(),
//             client_version: "clientversionidk".to_string(),
//         }));
//         match connection.send_packet(register_packet).await {
//             Ok(_) => println!("Sent registration packet to server."),
//             Err(e) => eprintln!("Failed to send registration packet: {}", e),
//         }
//     }
// }