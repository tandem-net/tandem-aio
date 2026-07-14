# Setting up a Tandem node (for partners)

This is the short list of commands to get a machine running as a Tandem node. The
node runs in the background, registers itself, and executes tasks. Once it's up,
`tandem status` tells you it's healthy, and you can `tandem deploy` / `tandem
start` jobs.

Replace `<SERVER_URL>` with the Tandem server you're connecting to (for example
`https://tandem.wnusair.org`).

You need **Python 3.10+** for the CLI on every platform. Building the node from
source additionally needs **Rust** (the installer tells you how to get it); or you
can install the node from a prebuilt package and skip Rust entirely.

---

## Linux

```bash
git clone <REPO_URL> tandem-aio
cd tandem-aio
./install.sh                              # installs the CLI and builds/installs the node

# if the installer says ~/.local/bin isn't on your PATH, add it and restart the shell:
#   export PATH="$HOME/.local/bin:$PATH"

tandem settings set-server-url <SERVER_URL>
tandem auth register                      # or: tandem auth login
tandem node enable                        # run 24/7 (starts on boot, restarts on crash)
tandem status                             # confirm: Node: running
```

Prefer a prebuilt package over building from source? Install the `.deb`, then run
the installer for just the CLI:

```bash
sudo dpkg -i tandem-node_<version>_amd64.deb
cd tandem-aio && TANDEM_SKIP_NODE=1 ./install.sh
# then the same settings / auth / enable / status steps as above
```

---

## macOS

```bash
git clone <REPO_URL> tandem-aio
cd tandem-aio
./install.sh                              # installs the CLI and builds/installs the node

tandem settings set-server-url <SERVER_URL>
tandem auth register                      # or: tandem auth login
tandem node enable                        # run 24/7 (starts on login, restarts on crash)
tandem status
```

Prefer the prebuilt `.dmg`? Open it, double-click **Install.command**, then run
`TANDEM_SKIP_NODE=1 ./install.sh` for the CLI and do the settings / auth / enable
/ status steps.

---

## Windows (PowerShell)

```powershell
git clone <REPO_URL> tandem-aio
cd tandem-aio
py -m pip install .\cli                   # installs the CLI

# Install the node binary: either build it (needs Rust)...
cargo build --release --manifest-path node\Cargo.toml
copy node\target\release\tandem-node.exe $HOME\.tandem\bin\tandem-node.exe
# ...or download tandem-node.exe from a release and put it in %USERPROFILE%\.tandem\bin\

tandem settings set-server-url <SERVER_URL>
tandem auth register                      # or: tandem auth login
tandem node start                         # runs in the background for this session
tandem status
```

Windows has no systemd/launchd, so `tandem node enable` isn't available there. Use
`tandem node start` to run the node in the background. To have it start
automatically at login, add a Task Scheduler task that runs
`%USERPROFILE%\.tandem\bin\tandem-node.exe` at logon.

---

## Everyday commands (all platforms)

```bash
tandem status          # login + node status
tandem node start      # start the node in the background
tandem node stop       # stop it
tandem node restart    # stop then start
tandem node status     # detailed node status
tandem node logs       # recent node output
tandem node enable     # run 24/7 (Linux/macOS)
tandem node disable    # turn 24/7 off
```

The node must be running before `tandem deploy` or `tandem start` will do
anything -- that's intentional. If you ever need to bypass that check (say in a
CI script), set `TANDEM_SKIP_NODE_CHECK=1`.
