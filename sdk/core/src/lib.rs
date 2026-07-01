//! Core Tandem SDK primitives for task packing and placeholder task submission.
//!
//! This crate intentionally keeps the first scaffold small: it defines the
//! task model, validates payloads, and simulates sending serialized work to a
//! downstream networking layer.

use std::error::Error;
use std::fmt;
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_TASK_ID: AtomicU64 = AtomicU64::new(1);

/// Result alias used across the Tandem core crate.
pub type Result<T> = std::result::Result<T, TandemCoreError>;

/// Errors surfaced by the placeholder Tandem core client.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TandemCoreError {
    /// The Python or SDK caller attempted to submit an empty payload.
    EmptyPayload,
    /// The client was configured with an unusable endpoint.
    InvalidEndpoint(String),
}

impl fmt::Display for TandemCoreError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyPayload => write!(formatter, "task payload cannot be empty"),
            Self::InvalidEndpoint(endpoint) => {
                write!(formatter, "client endpoint cannot be empty: {endpoint:?}")
            }
        }
    }
}

impl Error for TandemCoreError {}

/// Serialized work that can be handed off to Tandem's execution layer.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Task {
    pub id: String,
    pub payload: Vec<u8>,
    pub status: String,
}

impl Task {
    /// Builds a new task from a serialized payload.
    pub fn new(payload: Vec<u8>) -> Result<Self> {
        if payload.is_empty() {
            return Err(TandemCoreError::EmptyPayload);
        }

        let task_number = NEXT_TASK_ID.fetch_add(1, Ordering::Relaxed);

        Ok(Self {
            id: format!("task-{task_number}"),
            payload,
            status: "packed".to_string(),
        })
    }
}

/// Placeholder client responsible for packing and submitting serialized tasks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Client {
    endpoint: String,
}

impl Client {
    /// Creates a new placeholder client.
    pub fn new(endpoint: impl Into<String>) -> Result<Self> {
        let endpoint = endpoint.into();

        if endpoint.trim().is_empty() {
            return Err(TandemCoreError::InvalidEndpoint(endpoint));
        }

        Ok(Self { endpoint })
    }

    /// Returns the configured endpoint for inspection and logging.
    pub fn endpoint(&self) -> &str {
        &self.endpoint
    }

    /// Converts a raw byte slice into a `Task` instance.
    pub fn pack_task(&self, payload: &[u8]) -> Result<Task> {
        Task::new(payload.to_vec())
    }

    /// Simulates a network send by validating the payload and updating status.
    pub fn send_task(&self, task: &mut Task) -> Result<()> {
        if task.payload.is_empty() {
            return Err(TandemCoreError::EmptyPayload);
        }

        println!(
            "Simulating send of task {} ({} bytes) to {}",
            task.id,
            task.payload.len(),
            self.endpoint,
        );

        task.status.clear();
        task.status.push_str("submitted");

        Ok(())
    }

    /// Packs a payload into a task and pushes it through the placeholder send path.
    pub fn submit_task_bytes(&self, payload: &[u8]) -> Result<Task> {
        let mut task = self.pack_task(payload)?;
        self.send_task(&mut task)?;
        Ok(task)
    }
}

impl Default for Client {
    fn default() -> Self {
        Self {
            endpoint: "in-memory://tandem".to_string(),
        }
    }
}

/// Convenience entry point used by language bindings to submit a serialized task.
pub fn submit_task_bytes(payload: &[u8]) -> Result<Task> {
    Client::default().submit_task_bytes(payload)
}

#[cfg(test)]
mod tests {
    use super::{submit_task_bytes, Client, TandemCoreError};

    #[test]
    fn submits_non_empty_payloads() {
        let result = submit_task_bytes(b"serialized-function");
        assert!(result.is_ok());

        let task = match result {
            Ok(task) => task,
            Err(error) => panic!("expected a submitted task, received error: {error}"),
        };

        assert!(task.id.starts_with("task-"));
        assert_eq!(task.payload, b"serialized-function");
        assert_eq!(task.status, "submitted");
    }

    #[test]
    fn rejects_empty_payloads() {
        let result = submit_task_bytes(&[]);
        assert!(matches!(result, Err(TandemCoreError::EmptyPayload)));
    }

    #[test]
    fn validates_client_endpoint() {
        let result = Client::new("   ");
        assert!(matches!(result, Err(TandemCoreError::InvalidEndpoint(_))));
    }
}
