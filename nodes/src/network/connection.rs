use crate::network::packets::Packet;

pub enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

pub struct Connection {
    server_addr: String,
    status: ConnectionStatus,
}

impl Connection {
    pub fn new(server_addr: String) -> Self {
        Connection {
            server_addr,
            status: ConnectionStatus::Disconnected,
        }
    }

    pub async fn connect(&mut self) {
        self.status = ConnectionStatus::Connecting;
        // TODO: Implement websocket connection setup
    }


    fn send_packet(&self, packet: Packet) {
        if matches!(self.status, ConnectionStatus::Connected) {
            eprintln!("Cannot send packet: not connected");
            return;
        }

        // TODO: Implement send packet over websocket
    }
}