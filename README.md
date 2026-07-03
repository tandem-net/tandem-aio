# Tandem

## 1. Start the Server
```bash
cd server
pip install -r ../requirements.txt
flask --app app run --port 6767
```
*Starts the central Flask orchestration server on port 6767.*

## 2. Start a Compute Node
```bash
cd node
export TANDEM_SERVER_URL=http://127.0.0.1:6767
cargo run --release
```
*Compiles and runs a Rust node that registers with the server and polls for tasks.*

## 3. Install the CLI & SDK
```bash
cd cli
pip install -e .
```
*Installs the `tandem` CLI tool and Python SDK locally.*

## 4. Run a Project
```bash
# Initialize a new project config (tandem.toml)
tandem init

# Register a user and store credentials locally (.env)
tandem auth register --server-url http://127.0.0.1:6767

# Deploy the project to the server to get a PID
tandem deploy

# Compile tasks to WASM and start the job
tandem start
```
*Initializes, builds, and distributes your compute tasks across the network.*
