# Tandem Protocol v1

## Overview

Tandem distributes Python workloads across multiple Rust clients.

The server is responsible for:

- Creating tasks
- Serializing Python functions with cloudpickle
- Splitting work into batches
- Dispatching tasks to clients
- Collecting results

The client is responsible for:

- Receiving tasks
- Deserializing Python objects
- Executing Python code
- Returning serialized results
- Reporting status and health

---

# Execution Model

The protocol is built around the Rust API:

```rust
execute_python_tasks(
    func_obj: Bytes,
    args: Vec<Bytes>
)
```

The server sends:

```python
function_blob = cloudpickle.dumps(function)

invocation_blobs = [
    cloudpickle.dumps((arg1, arg2)),
    cloudpickle.dumps((arg3, arg4)),
    cloudpickle.dumps((arg5, arg6))
]
```

The client executes:

```python
func = cloudpickle.loads(function_blob)

for invocation_blob in invocation_blobs:
    args = cloudpickle.loads(invocation_blob)
    result = func(*args)
```

Results are serialized with:

```python
cloudpickle.dumps(result)
```

and sent back to the server.

---

# Packet Envelope

Every packet is wrapped inside a common envelope.

```json
{
  "packet_type": "task",
  "data": {}
}
```

## Why an Envelope Exists

Without an envelope, the receiver would not know which structure to deserialize.

The packet type determines:

- Which struct to parse
- Which handler to execute
- Whether the packet is valid for the current connection state

---

# Client Registration

## register

Direction:

```text
Client -> Server
```

Purpose:

Introduces a client to the server.

The server uses this packet to learn:

- Hardware capabilities
- Available RAM
- Available GPU
- Python version
- Client version

Example:

```text
Client starts
Client connects
Client sends register
```

The server should not schedule work until registration completes.

---

## register_ack

Direction:

```text
Server -> Client
```

Purpose:

Confirms registration.

Possible outcomes:

### Accepted

```json
{
  "accepted": true
}
```

Client enters normal operating state.

### Rejected

```json
{
  "accepted": false,
  "message": "client version unsupported"
}
```

Client should disconnect or attempt upgrade.

---

# Connection Health

## heartbeat

Direction:

```text
Client -> Server
```

Purpose:

Proves the client is still connected.

Recommended interval:

```text
Every 5 seconds
```

Server timeout:

```text
15-30 seconds
```

Example:

```text
12:00:00 heartbeat
12:00:05 heartbeat
12:00:10 heartbeat
```

If no heartbeat arrives:

```text
Client considered disconnected
Running tasks marked lost
```

Heartbeats are intentionally lightweight.

No system metrics should be included.

---

# Task Lifecycle

## task

Direction:

```text
Server -> Client
```

Purpose:

Assigns work to a client.

Contains:

### task_id

Unique identifier for the task.

Used for:

- Tracking
- Logging
- Result matching
- Cancellation

### submitted_at_unix_ms

Timestamp when the server created the task.

Useful for:

- Scheduling metrics
- Queue latency analysis

### function_blob

Contains:

```python
cloudpickle.dumps(function)
```

The Python function to execute.

### invocation_blobs

Contains:

```python
cloudpickle.dumps(tuple_of_args)
```

for each invocation.

Example:

```python
def add(a, b):
    return a + b
```

Server sends:

```python
cloudpickle.dumps((1, 2))
cloudpickle.dumps((3, 4))
cloudpickle.dumps((5, 6))
```

Client executes:

```python
add(1, 2)
add(3, 4)
add(5, 6)
```

The order of invocation_blobs matters.

Results must be returned in the same order.

---

## task_ack

Direction:

```text
Client -> Server
```

Purpose:

Confirms the task was received.

Sent immediately after parsing.

This prevents ambiguity.

Without task_ack:

```text
Did the packet arrive?
Did the client crash?
Did the network fail?
```

The server cannot know.

With task_ack:

```text
Server knows client accepted task
```

---

## task_result

Direction:

```text
Client -> Server
```

Purpose:

Returns completed work.

Contains:

### task_id

Matches the original task.

### started_at_unix_ms

Execution start timestamp.

### finished_at_unix_ms

Execution finish timestamp.

Used for:

- Performance tracking
- Throughput metrics
- Scheduling decisions

### results

Array of InvocationResult.

Result ordering must match invocation ordering.

Example:

```text
Invocation 0 -> Result 0
Invocation 1 -> Result 1
Invocation 2 -> Result 2
```

---

# InvocationResult

Each invocation returns one InvocationResult.

## Successful Invocation

```json
{
  "success": true,
  "result": "..."
}
```

result contains:

```python
cloudpickle.dumps(return_value)
```

---

## Failed Invocation

```json
{
  "success": false,
  "error": "division by zero"
}
```

Allows partial completion.

Example:

```python
add(1, 2) -> success
add(3, 0) -> failure
add(4, 5) -> success
```

The entire task does not need to fail.

---

## task_failed

Direction:

```text
Client -> Server
```

Purpose:

Reports catastrophic failure.

Examples:

```text
Unable to load cloudpickle
Out of memory
Function deserialization failed
Python interpreter crashed
```

Used when no useful results can be returned.

---

# Monitoring

## status_request

Direction:

```text
Server -> Client
```

Purpose:

Requests an immediate status update.

Useful when:

```text
Investigating slow clients
Building dashboards
Diagnosing issues
```

---

## status

Direction:

```text
Client -> Server
```

Purpose:

Reports current health.

Contains:

### state

Possible values:

```text
idle
executing
error
```

### current_task_id

Task currently being executed.

Null if idle.

### cpu_usage_percent

Current CPU utilization.

### memory_usage_percent

Current RAM utilization.

### gpu_usage_percent

Current GPU utilization.

Optional because some systems have no GPU.

### gpu_memory_percent

Current GPU memory utilization.

Optional.

Uses:

- Scheduler decisions
- Load balancing
- Monitoring dashboards
- Capacity planning

---

# Task Cancellation

## cancel_task

Direction:

```text
Server -> Client
```

Purpose:

Requests cancellation of a running task.

Reasons:

```text
User cancelled workload
Task timed out
Task reassigned
Server shutdown
```

Cancellation should be best effort.

Some Python workloads may not stop immediately.

---

# Error Handling

## error

Direction:

```text
Either Direction
```

Purpose:

Reports protocol-level failures.

Examples:

```text
Invalid packet
Malformed JSON
Unsupported protocol version
Unknown packet type
Authentication failure
```

Recommended error codes:

```text
1001 Invalid packet
1002 Deserialization failure
1003 Task not found
1004 Internal error
1005 Python runtime error
1006 Unsupported version
```

---

# Typical Workflow

```text
Client connects

register
register_ack

heartbeat
heartbeat
heartbeat

task
task_ack

client executes workload

task_result

heartbeat
heartbeat
heartbeat
```

---

# Packet Summary

Client -> Server

- register
- heartbeat
- task_ack
- status
- task_result
- task_failed
- error

Server -> Client

- register_ack
- task
- status_request
- cancel_task
- error
