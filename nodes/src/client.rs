// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::net::TcpStream;
use tokio::sync::mpsc;
use tokio::net::tcp::{OwnedReadHalf, OwnedWriteHalf};

use crate::network::{Packet, ClientState, TaskPayload, ResultPayload, send_packet, receive_packet, parse_packet};
use crate::run;

pub struct TandemClient {
    server_addr: String,
    state: Arc<Mutex<ClientState>>,
}

impl TandemClient {
    pub fn new(server_addr: String) -> Self {
        TandemClient {
            server_addr,
            state: Arc::new(Mutex::new(ClientState::new())),
        }
    }    
}