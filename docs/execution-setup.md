# Setting up a Tandem node (for partners)

This is the short list of commands to get a machine running as a Tandem node. The
node runs in the background, registers itself, and executes tasks. Once it's up,
`tandem status` tells you it's healthy, and you can `tandem deploy` / `tandem
start` jobs.

Replace `<SERVER_URL>` with the Tandem server you're connecting to (for example
`https://tandem.wnusair.org`).

You need **Python 3.10+** for the CLI on every platform. The node is a compiled
binary -- `install.sh` / `install.bat` build it from source if you have **Rust**,
otherwise they tell you how to drop in a prebuilt `tandem-node` binary. Installing
or updating is always the same one step: run the script.

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

---

## Windows

Open **Command Prompt** and run:

```bat
git clone <REPO_URL> tandem-aio
cd tandem-aio
install.bat

tandem settings set-server-url <SERVER_URL>
tandem auth register
tandem node start
tandem status
```

`install.bat` is the Windows twin of `install.sh`: it sets up a private Python
environment, puts a `tandem` command on your PATH, and installs the node
(building it if you have Rust, otherwise telling you how to drop in a prebuilt
`tandem-node.exe`). If it says the bin folder isn't on your PATH, follow its
instructions and open a new terminal.

Windows has no systemd/launchd, so `tandem node enable` isn't available there --
use `tandem node start` to run the node in the background. To have it start
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

## Uninstalling

```bash
tandem uninstall
```

This removes Tandem completely: it stops the node (and any 24/7 service), clears
your saved login, and deletes `~/.tandem` and the `tandem` command. Because
there's no undo, it prints a random 6-digit code you have to type back to
confirm -- type anything else and it does nothing.
