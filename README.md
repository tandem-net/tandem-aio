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

## 3. Install the CLI
```bash
./install.sh
```
*Sets up a private environment and puts the `tandem` command on your PATH. No Python packaging knowledge required.*

If you're working on the CLI itself, install it in editable mode instead:
```bash
cd cli
pip install -e .
```

## 4. Run a Project
```bash
# Initialize a new project config (tandem.toml)
tandem init

# Register a user and store credentials locally
tandem auth register --server-url http://127.0.0.1:6767

# Get the Python SDK so your task code can `import tandem`
tandem sdk install

# Deploy the project to the server to get a PID
tandem deploy

# Compile tasks to WASM and start the job
tandem start
```
*Initializes, builds, and distributes your compute tasks across the network.*
