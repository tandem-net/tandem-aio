// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};

use crate::network::connection::{self, Connection};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ClientState {
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
    pub fn new(server_addr: String) -> Self {
        TandemClient {
            server_addr,
            state: Arc::new(Mutex::new(ClientState::Idle)),
            connection: None,
        }
    }
    
    pub async fn connect(&mut self) {
        self.connection = Some(Connection::new(self.server_addr.clone()));
        if let Some(conn) = &mut self.connection {
            conn.connect().await;
        }
    }
    // TODO: Implement connection setup, client loop, task handling logic
    // module network; handles HTTP connection stuff
    // module run; handles deserialization, execution, and serialization of Python tasks
    // module main initializes the client
}