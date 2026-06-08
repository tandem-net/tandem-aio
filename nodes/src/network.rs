// network.rs
// sends and receives packets over TCP

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::time::{SystemTime, UNIX_EPOCH};
use sysinfo::{System, SystemExt, CpuExt};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

#[derive(Serialize, Deserialize, Debug)]
pub struct Packet {
    pub header: String,
    pub payload: Value,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct StatusInfo {
    pub idle: bool,
    pub running_task_id: Option<String>,
    pub cpu_usage: f32,
    pub memory_usage: f32,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct PingPayload {
    pub timestamp: u64,
    pub message: String,
    pub status: StatusInfo,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TaskPayload {
    pub task_id: String,
    pub timestamp: u64,
    pub func: Vec<u8>,
    pub args: Vec<Vec<u8>>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ResultPayload {
    pub task_id: String,
    pub timestamp: u64,
    pub result: Vec<u8>,
}

pub struct ClientState {
    pub idle: bool,
    pub running_task_id: Option<String>,
    system: System,
}

impl ClientState {
    pub fn new() -> Self {
        let mut system = System::new_all();
        system.refresh_all();
        ClientState {
            idle: true,
            running_task_id: None,
            system,
        }
    }

    pub fn get_status(&mut self) -> StatusInfo {
        self.system.refresh_cpu();
        self.system.refresh_memory();
        
        let cpu_usage = self.system.global_cpu_info().cpu_usage();
        let memory_usage = (self.system.used_memory() as f32 / self.system.total_memory() as f32) * 100.0;

        StatusInfo {
            idle: self.idle,
            running_task_id: self.running_task_id.clone(),
            cpu_usage,
            memory_usage,
        }
    }

    pub fn create_ping_payload(&mut self) -> PingPayload {
        let status = self.get_status();
        let timestamp = Self::get_current_timestamp();

        #[allow(clippy::collapsible_else_if)]
        PingPayload {
            timestamp,
            message: if self.idle {
                "task_request".to_string()
            } else {
                "busy".to_string()
            },
            status,
        }
    }

    pub fn get_current_timestamp() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
    }
}

// Sends a packet over any asynchronous writer
pub async fn send_packet<W>(
    stream: &mut W,
    packet: &Packet,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>>
where
    W: AsyncWriteExt + Unpin,
{
    let json_msg = serde_json::to_string(packet)?;
    let msg_with_newline = format!("{}\n", json_msg);

    stream.write_all(msg_with_newline.as_bytes()).await?;
    stream.flush().await?;

    Ok(())
}

// Receives raw chunk data from the stream
pub async fn receive_packet<R>(
    stream: &mut R,
    buffer: &mut [u8],
) -> Result<Option<String>, Box<dyn std::error::Error + Send + Sync>>
where
    R: AsyncReadExt + Unpin,
{
    match stream.read(buffer).await {
        Ok(0) => Ok(None),
        Ok(n) => {
            let message_str = String::from_utf8_lossy(&buffer[..n]).to_string();
            Ok(Some(message_str))
        }
        Err(e) => Err(Box::new(e)),
    }
}

pub fn parse_packet(data: &str) -> Result<Packet, Box<dyn std::error::Error + Send + Sync>> {
    let packet: Packet = serde_json::from_str(data)?;
    Ok(packet)
}