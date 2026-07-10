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

The CLI now bundles the runtime SDKs it knows about. Today that means a Python
project with `runtime = "python"` can be inspected and built without needing a
separate repo-relative SDK checkout. If you need to point at a custom SDK copy,
set `project.sdk_path` in `tandem.toml` (the legacy `project.sdk_python_path`
key still works too).

## Repo-local note

This repo also contains some older Node/TypeScript CLI scaffolding files in the
same folder. The current working path for the WASM pipeline is the **Python CLI**
under `cli/`.

## Commands

All commands that take a configuration path now default to checking `tandem.toml` or reading from the `TANDEM_CONFIG_PATH` environment variable if omitted. The CLI also automatically loads any `.env` file present in the current working directory, so your API keys are automatically picked up.

```bash
tandem init
tandem init [config_path] --name <project-name> --entry <python-entry-file>
tandem inspect [config_path]
tandem manifest [config_path]
tandem build [config_path]
tandem auth register --username <username>
tandem auth login --username <username>
tandem deploy [config_path]
tandem start [config_path]
tandem clean [config_path]
```

`tandem init`  works interactively by default: it asks a few quick questions, shows defaults, and lets you press Enter to accept them.

Interactive defaults:

- config path: `tandem.toml`
- project name: current directory name
- entry file: `tasks.py`
- version: `0.1.0`
- output directory: `.tandem_build/<project-name>`

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

### 4. Install the CLI command

From the repo root:

#### Linux / macOS

```bash
python -m pip install -e ./cli
```

#### Windows (PowerShell)

```powershell
py -m pip install -e .\cli
```

### 5. Create a user and store credentials locally

From the directory where you want Tandem to create or update `.env`:

#### Linux / macOS

```bash
tandem auth register --username demo --server-url http://127.0.0.1:6767
```

#### Windows (PowerShell)

```powershell
tandem auth register --username demo --server-url http://127.0.0.1:6767
```

The CLI prompts for your password securely, registers the user, authenticates, and stores `TANDEM_SERVER_URL` plus `TANDEM_API_KEY` in `.env`.

To authenticate an existing user instead:

```bash
tandem auth login --username demo --server-url http://127.0.0.1:6767
```

If you need a fresh API key, rotate it explicitly:

```bash
tandem auth login --username demo --rotate-api-key
```

Security notes:

- prefer the interactive password prompt over `--password`
- the CLI never stores your password in `.env`
- on POSIX systems it tightens `.env` permissions to owner read/write only
- use `--no-store` if you do not want the API key written to disk

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
