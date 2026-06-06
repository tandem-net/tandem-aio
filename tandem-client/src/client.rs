// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

// PING: 
// every 5 seconds
// send keepalive to server: Header: "ping"
// Payload: {
//     "timestamp": (current time)
//     message: "task_request" if needs job
//     status: {
//         "idle": (bool)
//         "running_task_id": (if not idle)
//         "cpu_usage": (current cpu usage)
//         "memory_usage": (current memory usage)
//     }
// }

// FUNCTIONALITY:
// receives from go server request:
// Header: "task"
// Payload: {
//     "task_id": 
//     "timestamp": (creation)
//     "func": (serialized python)
//     "args": (list of serialized python args)
// }

// network gets the task and passes to client via fn returns
// client handles all the processing: passes deserialized data to run.rs which executes it
// run.rs executes the python deserialized code and returns serialized result
// client serializes result and sends back to server:
// Header: "result"
// Payload: {
//     "task_id": (same as request)
//     "timestamp": (completion)
//     "result": (serialized python result)
// }

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

    pub async fn connect(&self) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let stream = TcpStream::connect(&self.server_addr).await?;
        println!("Connected to server at {}", self.server_addr);

        let (read_half, write_half) = stream.into_split();
        
        // MPSC channel to pipeline outbound network packets safely
        let (tx, rx) = mpsc::channel::<Packet>(32);

        // 1. Spawn Outbound Network Driver Loop
        tokio::spawn(Self::write_loop(write_half, rx));

        // 2. Spawn Inbound Keepalive Ping Loop
        let ping_tx = tx.clone();
        let state_clone = Arc::clone(&self.state);
        tokio::spawn(Self::ping_loop(state_clone, ping_tx));

        // 3. Process main task worker incoming flow
        self.message_loop(read_half, tx).await?;

        Ok(())
    }

    async fn write_loop(mut write_stream: OwnedWriteHalf, mut rx: mpsc::Receiver<Packet>) {
        while let Some(packet) = rx.recv().await {
            if let Err(e) = send_packet(&mut write_stream, &packet).await {
                eprintln!("Network writer loop error: {}", e);
                break;
            }
        }
    }

    async fn ping_loop(
        state: Arc<Mutex<ClientState>>,
        tx: mpsc::Sender<Packet>,
    ) {
        loop {
            tokio::time::sleep(Duration::from_secs(crate::PING_INTERVAL_SECS)).await;

            let mut client_state = match state.lock() {
                Ok(guard) => guard,
                Err(poisoned) => poisoned.into_inner(),
            };
            let ping_payload = client_state.create_ping_payload();

            if let Ok(val) = serde_json::to_value(&ping_payload) {
                let packet = Packet {
                    header: "ping".to_string(),
                    payload: val,
                };
                if tx.send(packet).await.is_err() {
                    break; // Connection dropped
                }
            }
        }
    }

    async fn message_loop(
        &self,
        mut read_stream: OwnedReadHalf,
        tx: mpsc::Sender<Packet>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let mut buffer = [0; crate::BUFFER_SIZE];

        loop {
            match receive_packet(&mut read_stream, &mut buffer).await {
                Ok(None) => {
                    println!("Server closed socket connection.");
                    break;
                }
                Ok(Some(message_str)) => {
                    for line in message_str.lines() {
                        if line.is_empty() {
                            continue;
                        }

                        match parse_packet(line) {
                            Ok(packet) => {
                                if packet.header == "task" {
                                    let task_tx = tx.clone();
                                    self.process_task(&packet.payload, task_tx).await?;
                                } else {
                                    println!("Unknown header event: {}", packet.header);
                                }
                            }
                            Err(e) => eprintln!("Corrupt packet JSON structure: {}", e),
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Socket socket read exception: {}", e);
                    break;
                }
            }
        }
        Ok(())
    }

    async fn process_task(
        &self,
        payload: &serde_json::Value,
        tx: mpsc::Sender<Packet>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let task: TaskPayload = serde_json::from_value(payload.clone())?;
        println!("Initializing Task Execution Context: {}", task.task_id);

        {
            let mut state = self.state.lock().unwrap();
            state.idle = false;
            state.running_task_id = Some(task.task_id.clone());
        }

        let result = match self.execute_task(&task).await {
            Ok(res) => res,
            Err(e) => {
                eprintln!("Compute Engine failure execution context: {}", e);
                vec![]
            }
        };

        {
            let mut state = self.state.lock().unwrap();
            state.idle = true;
            state.running_task_id = None;
        }

        self.send_result(tx, &task.task_id, result).await?;
        Ok(())
    }

    async fn execute_task(
        &self,
        task: &TaskPayload,
    ) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        let func_obj = crate::serialization::deserialize(&task.func)?;
        let args: Vec<Vec<u8>> = task.args.iter()
            .map(|arg| crate::serialization::deserialize(arg))
            .collect::<Result<Vec<_>, _>>()?;

        let result = run::execute_python_task(func_obj, args).await?;
        let serialized_result = crate::serialization::serialize(&result)?;

        Ok(serialized_result)
    }

    async fn send_result(
        &self,
        tx: mpsc::Sender<Packet>,
        task_id: &str,
        result: Vec<u8>,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        let result_payload = ResultPayload {
            task_id: task_id.to_string(),
            timestamp: ClientState::get_current_timestamp(),
            result,
        };

        let packet = Packet {
            header: "result".to_string(),
            payload: serde_json::to_value(&result_payload)?,
        };

        tx.send(packet).await.map_err(|_| "Failed to forward output to write loop channel")?;
        println!("Task completed execution. Result pushed to network queue: {}", task_id);
        Ok(())
    }
}