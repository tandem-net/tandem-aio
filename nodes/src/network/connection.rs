use futures_util::SinkExt;
use tokio::net::TcpStream;
use tokio_tungstenite::{MaybeTlsStream, WebSocketStream, connect_async, tungstenite::{Error, Message}};

use crate::network::packets::{Packet, PacketType};

pub enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

pub struct Connection {
    server_addr: String,
    status: ConnectionStatus,
    ws_stream: Option<WebSocketStream<MaybeTlsStream<TcpStream>>>,
}

impl Connection {
    pub fn new(server_addr: String) -> Self {
        Connection {
            server_addr,
            status: ConnectionStatus::Disconnected,
            ws_stream: None,
        }
    }

    pub async fn connect(&mut self) -> Result<(), Error> {
        self.status = ConnectionStatus::Connecting;
        // TODO: Implement websocket connection setup
        let url = "ws://".to_string() + &self.server_addr + "/ws";
        let (stream, _) = match connect_async(url).await {
            Ok(result) => result,
            Err(e) => {
                self.status = ConnectionStatus::Error(e.to_string());
                return Err(e);
            }
        };
        self.ws_stream = Some(stream);
        self.status = ConnectionStatus::Connected;
        Ok(())
    }

    pub async fn send_packet_type(&mut self, packet_type: PacketType) {
        self.send_packet(Packet::new(packet_type));
    }

    pub async fn send_packet(&mut self, packet: Packet) -> Result<(), Error> {
        if !matches!(self.status, ConnectionStatus::Connected) {
            eprintln!("Cannot send packet: not connected");
            return Err(Error::AlreadyClosed);
        }

        let json = serde_json::to_string(&packet)
        .expect("Failed to serialize packet");

        if let Some(stream) = &mut self.ws_stream {
            stream.send(Message::Text(json.into())).await?;
        }

        Ok(())
    }
}