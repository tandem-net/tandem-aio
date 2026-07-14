# Setting up a Tandem node (for partners)

This is the short list of commands to get a machine running as a Tandem node. The
node runs in the background, registers itself, and executes tasks. Once it's up,
`tandem status` tells you it's healthy, and you can `tandem deploy` / `tandem
start` jobs.

Replace `<SERVER_URL>` with the Tandem server you're connecting to (for example
`https://tandem.wnusair.org`).

You need **Python 3.10+** for the CLI on every platform. The node is a compiled
binary -- the installer builds it from source if you have **Rust**, otherwise you
point it at a prebuilt binary (see
[Building the downloadable packages](#building-the-downloadable-packages-deb--dmg--exe)
at the bottom).

> **Note:** the `.deb`, `.dmg`, and `.exe` are **not** checked into the repo --
> they're compiled artifacts (~20 MB each), so you either let `install.sh` /
> `install.bat` build the node for you, or you build a package yourself with the
> commands at the bottom, or you download one from a release.

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

Prefer a prebuilt package over building from source? Build (or download) the
`.deb`, install it, then run the installer for just the CLI:

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

---

## Building the downloadable packages (.deb / .dmg / .exe)

Yes -- these are built on demand, not shipped in the repo. Each one is built on
its own OS (that's the reliable way; cross-building a `.dmg` or `.exe` from Linux
is a headache). Build outputs land in `node/packaging/dist/`.

**Linux `.deb`** -- on any machine with `dpkg-deb`:

```bash
bash node/packaging/build-deb.sh
# -> node/packaging/dist/tandem-node_<version>_amd64.deb
sudo dpkg -i node/packaging/dist/tandem-node_*.deb      # to install it locally
```

**macOS `.dmg`** -- on a Mac:

```bash
bash node/packaging/build-dmg.sh
# -> node/packaging/dist/tandem-node-macos-<arch>.dmg
```

**Windows `.exe`** -- on Windows with Rust (the binary itself is the deliverable):

```bat
cargo build --release --manifest-path node\Cargo.toml
REM ship node\target\release\tandem-node.exe
```

**All three at once (CI)** -- you can't make a `.dmg` or `.exe` on Linux, so the
real cross-platform build lives in
[`.github/workflows/release.yml`](../.github/workflows/release.yml). Push a version
tag and it builds every package on its own runner and attaches them to a GitHub
Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

More detail in [node/packaging/README.md](../node/packaging/README.md).
