# Tandem

Tandem runs your compute tasks across a network of nodes. You write tasks against
the Tandem SDK, the CLI builds and ships them, and a **node** running on your
machine actually executes them. The CLI installs and manages that node for you.

## 1. Start the server

```bash
cd server
pip install -r ../requirements.txt
flask --app app run --port 6767
```
*Starts the central Flask orchestration server on port 6767.*

## 2. Install the CLI and the node

```bash
./install.sh
```
*Sets up a private environment, puts the `tandem` command on your PATH, and builds
and installs the compute node (`tandem-node`) into `~/.tandem/bin`. No Python or
Rust packaging knowledge required.* If Rust isn't installed, the script tells you
exactly how to get it or how to drop in a prebuilt binary instead.

If you're working on the CLI itself, install it in editable mode instead:
```bash
cd cli
pip install -e .
```

## 3. Log in and start your node

```bash
# Point the CLI at your server (saved, so you don't repeat it everywhere)
tandem settings set-server-url http://127.0.0.1:6767

# Log in (or `tandem auth register` for a new account)
tandem auth login

# Start your node in the background -- it registers itself the first time
tandem node start

# ...or run it 24/7 (starts on boot, restarts if it crashes)
tandem node enable

# See your login and whether the node is running
tandem status
```

Your node has to be running before you can deploy or start a job -- that's the
point of it. If it's down, `deploy` and `start` stop and tell you to start it.

## 4. Run a project

```bash
# Initialize a new project config (tandem.toml)
tandem init

# Get the Python SDK so your task code can `import tandem`
tandem sdk install

# Deploy the project to the server to get a PID
tandem deploy

# Compile tasks to WASM and start the job
tandem start
```
*Initializes, builds, and distributes your compute tasks across the network.*

## Managing the node

```bash
tandem node start      # start it in the background
tandem node stop       # stop it
tandem node restart    # stop then start
tandem node status     # is it running? what's its id?
tandem node logs       # recent output from the node
tandem node enable     # run 24/7 as an OS service (systemd/launchd)
tandem node disable    # turn that off, back to manual start/stop
```

## Downloadable node binaries

You can also install the node from a prebuilt package instead of building it:

- **Linux** — a `.deb`: `sudo dpkg -i tandem-node_<version>_amd64.deb`
- **macOS** — a `.dmg`: open it and double-click `Install.command`
- **Windows** — a `.exe`: drop `tandem-node.exe` somewhere on your PATH

See [node/packaging/README.md](node/packaging/README.md) for how these are built
(a `git push` of a `v*` tag builds all three on CI and attaches them to a release).
