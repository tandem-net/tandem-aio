// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};

use crate::network::{connection::Connection, packets::{Packet, PacketType, RegisterPacket}};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClientState {
    Disconnected,
    Idle,
    Executing,
    Error,
}


pub struct TandemClient {
    server_addr: String,
    state: Arc<Mutex<ClientState>>,
    connection: Option<Connection>,
}

impl TandemClient {
    pub fn get_state(&self) -> ClientState {
        self.state.lock().unwrap().clone()
    }

    pub fn get_connection(&mut self) -> Option<&mut Connection> {
        self.connection.as_mut()
    }

    pub fn new(server_addr: String) -> Self {
        TandemClient {
            server_addr,
            state: Arc::new(Mutex::new(ClientState::Disconnected)),
            connection: None,
        }
    }
    
    pub async fn connect(&mut self) {
        self.connection = Some(Connection::new(self.server_addr.clone()));
        if let Some(connection) = &mut self.connection {
            match connection.connect().await {
                Ok(_) => {
                    println!("Connected to server successfully.");
                    self.state = Arc::new(Mutex::new(ClientState::Idle));
                    let register_packet = Packet::new(PacketType::Register(RegisterPacket {
                        client_id: "client123".to_owned(),
                        hostname: "testmachine".to_string(),
                        cpu_cores: 4,
                        memory_bytes: 16 * 1024 * 1024 * 1024,
                        gpu_name: Some("pee".to_owned()),
                        gpu_memory_bytes: Some(8 * 1024 * 1024 * 1024),
                        python_version: "realpyversion".to_string(),
                        client_version: "clientversionidk".to_string(),
                    }));
                    match connection.send_packet(register_packet).await {
                        Ok(_) => println!("Sent registration packet to server."),
                        Err(e) => eprintln!("Failed to send registration packet: {}", e),
                    }
                },
                Err(e) => eprintln!("Failed to connect to server: {}", e),
            }
        }
    }
    // TODO: Implement client loop, task handling logic
    // module network; handles HTTP connection stuff
    // module run; handles deserialization, execution, and serialization of Python tasks
    // module main initializes the client
}