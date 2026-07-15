# Packaging Tandem

These scripts turn Tandem into downloadable installers -- one file a person can
double-click to get the commands on their PATH:

- **`tandem`** -- the command-line tool (a Python app frozen into a single binary)
- **`tandem-node`** -- the compute node it drives (a Rust binary)
- **`tandem-compile`** -- the compile engine `tandem build` shells out to (a Rust binary)

The goal is that a package gives you what `install.sh` gives you, just shipped as a
file instead of run from a source checkout. The one thing a package can't bundle
is componentize-py (the Python toolchain `tandem-compile` calls to lower Python
into WASM), so a package is everything you need to run a node and
deploy/start/serve out of the box; `tandem build` also works once componentize-py
is on the machine. See "How this fits together" below.

## The pieces

The build is layered so nothing is circular: each binary knows how to build
itself, and the installers just collect the finished binaries.

| What | Built by | Output |
|------|----------|--------|
| the node binary | `cargo build --release` (in `node/`) | `node/target/release/tandem-node` |
| the compile engine | `cargo build --release --bin tandem-compile` (in `sdk/`) | `sdk/target/release/tandem-compile` |
| the CLI binary  | [`cli/packaging/build-binary.sh`](../cli/packaging/build-binary.sh) | `cli/packaging/dist/tandem` |
| Linux `.deb`    | [`build-deb.sh`](build-deb.sh) | `packaging/dist/tandem_<version>_<arch>.deb` |
| macOS `.dmg`    | [`build-dmg.sh`](build-dmg.sh) | `packaging/dist/tandem-macos-<arch>.dmg` |

`build-deb.sh` reuses the two Rust binaries if they're already built (they only
change when you recompile them) but always rebuilds the CLI binary, so the package
never ships stale CLI code. Then it wraps everything up -- just run the installer
builder and it handles the rest.

## Build one locally

```bash
# Linux .deb  ->  packaging/dist/tandem_<version>_<arch>.deb
bash packaging/build-deb.sh

# macOS .dmg  ->  packaging/dist/tandem-macos-<arch>.dmg   (run on a Mac)
bash packaging/build-dmg.sh
```

Building the `.deb` needs `dpkg-deb` (part of the base system on Debian/Ubuntu;
`brew install dpkg` on macOS). Building the CLI binary needs Python 3.10+ -- the
script creates its own throwaway virtualenv, so it won't touch your system
Python.

## Windows

Windows doesn't get a bundled package yet -- use [`install.bat`](../install.bat)
from the repo root, which is the Windows twin of `install.sh` (it sets up the
`tandem` command and builds/installs the node). The released Windows `.exe` is
just the standalone `tandem-node` binary for people who want to drop the node in
by hand.

## Build all of them at once (CI)

You can't make a `.dmg` on a Linux box, so the real cross-platform build lives in
[`.github/workflows/release.yml`](../.github/workflows/release.yml). Push a
version tag and it builds each package on its own native runner and attaches them
to a GitHub Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Or run it by hand from the Actions tab (workflow_dispatch) to check the builds
without publishing.

## After installing a package

However the binaries got onto the machine, you drive everything from the CLI:

```bash
tandem auth login      # log in
tandem node start      # start the node in the background
tandem node enable     # run it 24/7 (starts on boot/login, restarts on crash)
tandem status          # is it running?
```

The `.deb` installs the binaries to `/usr/bin`, the `.dmg`'s installer copies
them to `/usr/local/bin`, and `install.sh` puts them under `~/.tandem` -- the CLI
finds the node in any of those plus your `PATH`.

## How this fits together (packages vs install.sh)

Both a package and `install.sh` end with the same two commands on your PATH.
They just suit different situations:

- **`install.sh` / `install.bat`** run from a source checkout. They install the
  CLI into a private virtualenv and build the node from source (or drop in a
  prebuilt one). This is the developer path -- re-running picks up your local
  code changes immediately.
- **The `.deb` / `.dmg`** are for people who just want to install and run a node.
  They ship the already-built binaries, so there's no Python, pip, or Rust needed
  to run the node or deploy/start/serve -- just the one file. Building tasks
  (`tandem build`) additionally needs componentize-py on the machine, which is why
  developers who build usually take the `install.sh` path.

So they're not doing different *things*; they're two ways to land the same result.
