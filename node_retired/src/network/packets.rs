use serde::{Deserialize, Serialize};

use crate::client::ClientState;

use std::sync::atomic::{AtomicU64, Ordering};

pub type TaskId = String;

static PACKET_COUNTER: AtomicU64 = AtomicU64::new(1);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Packet {
    pub protocol_version: u16,
    pub packet_id: u64,

    #[serde(flatten)]
    pub packet: PacketType,
}

impl Packet {
    pub fn new(packet: PacketType) -> Self {
        Self {
            protocol_version: 1,
            packet_id: PACKET_COUNTER.fetch_add(1, Ordering::Relaxed),
            packet,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "packet_type", content = "data")]
#[serde(rename_all = "snake_case")]
pub enum PacketType {
    Register(RegisterPacket),
    RegisterAck(RegisterAckPacket),
    Heartbeat(HeartbeatPacket),
    Task(TaskPacket),
    TaskAck(TaskAckPacket),
    TaskResult(TaskResultPacket),
    TaskFailed(TaskFailedPacket),
    Status(StatusPacket),
    StatusRequest(StatusRequestPacket),
    CancelTask(CancelTaskPacket),
    Error(ErrorPacket),
}

//
// Client -> Server
//

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterPacket {
    pub client_id: String,
    pub hostname: String,

    pub cpu_cores: u32,
    pub memory_bytes: u64,

    pub gpu_name: Option<String>,
    pub gpu_memory_bytes: Option<u64>,

    pub python_version: String,
    pub client_version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeartbeatPacket {
    pub timestamp_unix_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskAckPacket {
    pub task_id: TaskId,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusPacket {
    pub state: ClientState,

    pub current_task_id: Option<TaskId>,

    pub cpu_usage_percent: f32,
    pub memory_usage_percent: f32,

    pub gpu_usage_percent: Option<f32>,
    pub gpu_memory_percent: Option<f32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvocationResult {
    pub success: bool,

    pub result: Option<Vec<u8>>,

    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResultPacket {
    pub task_id: TaskId,

    pub started_at_unix_ms: u64,
    pub finished_at_unix_ms: u64,

    pub results: Vec<InvocationResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskFailedPacket {
    pub task_id: TaskId,

    pub message: String,
}

//
// Server -> Client
//

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegisterAckPacket {
    pub accepted: bool,

    pub message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskPacket {
    pub task_id: TaskId,

    pub submitted_at_unix_ms: u64,

    /// cloudpickle.dumps(function)
    pub function_blob: Vec<u8>,

    /// Vec of cloudpickle.dumps(tuple(args))
    pub invocation_blobs: Vec<Vec<u8>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusRequestPacket {}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CancelTaskPacket {
    pub task_id: TaskId,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorPacket {
    pub code: u32,

    pub message: String,
}