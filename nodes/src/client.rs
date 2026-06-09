// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

use std::sync::{Arc, Mutex};
use crate::{network::ClientState};

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
    
    // TODO: Implement connection setup, client loop, task handling logic
    // module network; handles HTTP connection stuff
    // module run; handles deserialization, execution, and serialization of Python tasks
    // module main initializes the client
}