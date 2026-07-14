# Packaging the Tandem node

The node is a single Rust binary (`tandem-node`). These scripts turn a release
build into a downloadable installer for each platform. The guiding idea is that
each package is built on its own native OS -- that's the most reliable, most
transferable way, so we don't fight cross-compilation.

| Platform | Artifact | How it's built | Runs on |
|----------|----------|----------------|---------|
| Linux    | `.deb`   | `build-deb.sh` (uses `dpkg-deb`) | Linux, or any box with dpkg |
| macOS    | `.dmg`   | `build-dmg.sh` (uses `hdiutil`)  | macOS only |
| Windows  | `.exe`   | the raw `cargo build` output     | anywhere (it's just the binary) |

## Build one locally

```bash
# Linux .deb  ->  node/packaging/dist/tandem-node_<version>_<arch>.deb
bash node/packaging/build-deb.sh

# macOS .dmg  ->  node/packaging/dist/tandem-node-macos-<arch>.dmg   (run on a Mac)
bash node/packaging/build-dmg.sh
```

On Windows, the binary itself is the deliverable -- after `cargo build --release
--manifest-path node/Cargo.toml`, ship `node/target/release/tandem-node.exe`.

## Build all three at once (CI)

You can't make a `.exe` or `.dmg` on a Linux machine, so the real cross-platform
build lives in [`.github/workflows/release.yml`](../../.github/workflows/release.yml).
Push a version tag and it builds every package on its own runner and attaches
them to a GitHub Release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Or run it by hand from the Actions tab (workflow_dispatch) to check the builds
without publishing.

## After installing a package

However the binary got onto the machine, the Tandem CLI takes it from there:

```bash
tandem node start     # start it in the background
tandem node enable    # run it 24/7 (starts on boot/login, restarts on crash)
tandem status         # is it running?
```

The `.deb` installs to `/usr/bin`, the `.dmg`'s installer copies to
`/usr/local/bin`, and `install.sh` puts it in `~/.tandem/bin` -- the CLI checks
all of those plus your `PATH`.
