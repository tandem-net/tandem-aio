# Tandem CLI

This folder contains the **active Python CLI** for Tandem.

The important bit is: after installing it, you run **`tandem`** directly.
You do **not** need to run `python cli/main.py` or `python cli/cli.py` anymore.

## Install the command

The CLI is packaged with a Python console entry point:

- Linux/macOS: installs a `tandem` shell command
- Windows: installs a `tandem.exe` launcher

### Linux / macOS

```bash
python -m pip install -e ./cli
```

### Windows (PowerShell)

```powershell
py -m pip install -e .\cli
```

Then verify it:

```bash
tandem --help
```

## Repo-local note

This repo also contains some older Node/TypeScript CLI scaffolding files in the
same folder. The current working path for the WASM pipeline is the **Python CLI**
under `cli/tandem_cli/`.

## Commands

```bash
tandem init <config.toml> --name <project-name> --entry <python-entry-file>
tandem inspect <config.toml>
tandem manifest <config.toml>
tandem build <config.toml>
tandem deploy <config.toml> --api-key <api-key>
tandem start <config.toml> --api-key <api-key>
tandem clean <config.toml>
```

## Full local flow

This is the smallest end-to-end flow for the current repo.

### 1. Start the server dependencies

You need Redis running.

#### Linux / macOS

```bash
redis-server
```

#### Windows

Use Redis in WSL, Docker, or a local Redis install, then make sure the server can
reach it.

### 2. Start the Flask server

From the repo root:

#### Linux / macOS

```bash
export REDIS_URL=redis://127.0.0.1:6379/0
export TANDEM_NODE_REGISTRATION_TOKEN=meow-secret
python server/run.py
```

#### Windows (PowerShell)

```powershell
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:TANDEM_NODE_REGISTRATION_TOKEN = "meow-secret"
py server/run.py
```

The server listens on `http://127.0.0.1:6767` by default.

### 3. Start a node

From the repo root, in another terminal:

#### Linux / macOS

```bash
export TANDEM_SERVER_URL=http://127.0.0.1:6767
export TANDEM_NODE_REGISTRATION_TOKEN=meow-secret
cargo run --manifest-path node/Cargo.toml
```

#### Windows (PowerShell)

```powershell
$env:TANDEM_SERVER_URL = "http://127.0.0.1:6767"
$env:TANDEM_NODE_REGISTRATION_TOKEN = "meow-secret"
cargo run --manifest-path node/Cargo.toml
```

If you actually want the big startup bandwidth benchmark, opt into it:

#### Linux / macOS

```bash
export TANDEM_NODE_BENCHMARK_STARTUP=1
```

#### Windows (PowerShell)

```powershell
$env:TANDEM_NODE_BENCHMARK_STARTUP = "1"
```

Otherwise the node starts leaner and just registers itself as WASM-capable.

### 4. Create a user and API key

Use the server API once.

#### Linux / macOS

```bash
curl -X POST http://127.0.0.1:6767/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo-pass"}'

curl -X POST http://127.0.0.1:6767/api/v1/generate_api \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo-pass"}'
```

#### Windows (PowerShell)

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:6767/api/v1/register `
  -ContentType "application/json" `
  -Body '{"username":"demo","password":"demo-pass"}'

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:6767/api/v1/generate_api `
  -ContentType "application/json" `
  -Body '{"username":"demo","password":"demo-pass"}'
```

Save the returned `api_key`.

### 5. Install the CLI command

From the repo root:

#### Linux / macOS

```bash
python -m pip install -e ./cli
export TANDEM_API_KEY=<your-api-key>
export TANDEM_SERVER_URL=http://127.0.0.1:6767
```

#### Windows (PowerShell)

```powershell
py -m pip install -e .\cli
$env:TANDEM_API_KEY = "<your-api-key>"
$env:TANDEM_SERVER_URL = "http://127.0.0.1:6767"
```

### 6. Build and run the sample project

From the repo root:

```bash
tandem start cli/test.toml
```

That command will:

1. inspect the Python entry file,
2. build the placeholder `.wasm` artifacts,
3. create a deployment if needed,
4. upload the TOML + manifest + wasm files,
5. wait for node execution,
6. print the returned results.

If you want to just create the deployment first:

```bash
tandem deploy cli/test.toml
```

If you already have a deployment pid and want to reuse it:

```bash
tandem start cli/test.toml --pid <deployment-pid>
```

If you want to queue the job without waiting:

```bash
tandem start cli/test.toml --no-wait
```

That prints the `job_token`, status URL, and results URL.

## Current runtime limitation

The transport pipeline is live, but the current Python build backend still emits
**placeholder WASM**. So a successful run proves the CLI → server → node → server
path works, but it does not yet mean arbitrary Python logic has been lowered into
real native WASM instructions.
