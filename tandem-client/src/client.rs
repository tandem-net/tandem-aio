// client.rs
// handles all the processing: receives tasks from network, passes to run.rs for execution

use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::net::TcpStream;

use crate::network::{Packet, ClientState, TaskPayload, ResultPayload, send_packet, receive_packet, parse_packet};
use crate::run;

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

    pub async fn connect(&self) -> Result<(), Box<dyn std::error::Error>> {
        let stream = TcpStream::connect(&self.server_addr).await?;
        
        println!("Connected to server at {}", self.server_addr);

        let stream_clone = stream.try_clone()?;
        let state_clone = Arc::clone(&self.state);
        
        // Spawn ping loop
        tokio::spawn(Self::ping_loop(state_clone, stream_clone));

        // Main message receiving loop
        self.message_loop(stream).await?;

        Ok(())
    }

    async fn ping_loop(
        state: Arc<Mutex<ClientState>>,
        mut stream: TcpStream,
    ) -> Result<(), Box<dyn std::error::Error>> {
        loop {
            tokio::time::sleep(Duration::from_secs(crate::PING_INTERVAL_SECS)).await;

            let mut client_state = state.lock().unwrap();
            let ping_payload = client_state.create_ping_payload();

            let packet = Packet {
                header: "ping".to_string(),
                payload: serde_json::to_value(&ping_payload)?,
            };

            match send_packet(&mut stream, &packet).await {
                Ok(_) => {
                    println!("Sent ping: {:?}", ping_payload);
                }
                Err(e) => {
                    eprintln!("Failed to send ping: {}", e);
                    break;
                }
            }
        }
    }

    async fn message_loop(
        &self,
        mut stream: TcpStream,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let mut buffer = [0; crate::BUFFER_SIZE];

        loop {
            match receive_packet(&mut stream, &mut buffer).await {
                Ok(None) => {
                    println!("Server disconnected");
                    break;
                }
                Ok(Some(message_str)) => {
                    for line in message_str.lines() {
                        if line.is_empty() {
                            continue;
                        }

                        match parse_packet(line) {
                            Ok(packet) => {
                                match packet.header.as_str() {
                                    "task" => {
                                        let stream_clone = stream.try_clone()?;
                                        self.process_task(&packet.payload, stream_clone).await?;
                                    }
                                    _ => {
                                        println!("Unknown packet header: {}", packet.header);
                                    }
                                }
                            }
                            Err(e) => {
                                eprintln!("Failed to parse packet: {}", e);
                            }
                        }
                    }
                }
                Err(e) => {
                    eprintln!("Read error: {}", e);
                    break;
                }
            }
        }

        Ok(())
    }

    async fn process_task(
        &self,
        payload: &serde_json::Value,
        mut stream: TcpStream,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let task: TaskPayload = serde_json::from_value(payload.clone())?;

        println!("Received task: {}", task.task_id);

        // Update state - mark as busy
        {
            let mut state = self.state.lock().unwrap();
            state.idle = false;
            state.running_task_id = Some(task.task_id.clone());
        }

        // Deserialize function and args, pass to run.rs for execution
        let result = match self.execute_task(&task).await {
            Ok(res) => res,
            Err(e) => {
                eprintln!("Task execution error: {}", e);
                vec![]
            }
        };

        // Update state - mark as idle
        {
            let mut state = self.state.lock().unwrap();
            state.idle = true;
            state.running_task_id = None;
        }

        // Send result back via network
        self.send_result(&mut stream, &task.task_id, result).await?;

        Ok(())
    }

    async fn execute_task(
        &self,
        task: &TaskPayload,
    ) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
        println!("Executing task: {}", task.task_id);

        // Deserialize the function and arguments
        let func_obj = crate::serialization::deserialize(&task.func)?;
        let args: Vec<Vec<u8>> = task.args.iter()
            .map(|arg| crate::serialization::deserialize(arg))
            .collect::<Result<Vec<_>, _>>()?;

        // Pass to run.rs for execution
        let result = run::execute_python_task(func_obj, args).await?;

        // Serialize the result
        let serialized_result = crate::serialization::serialize(&result)?;

        Ok(serialized_result)
    }

    async fn send_result(
        &self,
        stream: &mut TcpStream,
        task_id: &str,
        result: Vec<u8>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let result_payload = ResultPayload {
            task_id: task_id.to_string(),
            timestamp: ClientState::get_current_timestamp(),
            result,
        };

        let packet = Packet {
            header: "result".to_string(),
            payload: serde_json::to_value(&result_payload)?,
        };

        send_packet(stream, &packet).await?;

        println!("Sent result for task: {}", task_id);

        Ok(())
    }
}