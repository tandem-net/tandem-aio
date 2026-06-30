# Tandem CLI

Build tool that scans a project for Tandem tasks, validates them, packages
them into a `.tandem` artifact, and uploads that artifact to the Tandem
server.

## What this CLI actually does today

**Scan** -- walks the project for source files, and for Python files,
detects `@tandem.compute(...)` and `name = tandem.split(fn, ...)` task
definitions, extracting the same metadata shape the Python SDK produces
(name, entry, language, execution class, split hints, immutable bundle
names referenced).

**Validate** -- shells out to a real Python process and imports each
task's source module. Since the SDK's `@tandem.compute` / `tandem.split`
validate split-independence *eagerly at decoration time* (see
`sdk/python-sdk/tandem/validator.py`), simply importing the module is
enough to trigger the real AST-based check. If a task isn't
independent, the import raises `TandemValidationError` and the build
fails with that exact message. **This means the CLI never re-implements
Python semantics in TypeScript** -- there's exactly one validator, and
it's the Python one.

**Compile** -- for Python, bundles the task's metadata JSON and raw
source into a small, real, structurally-valid WASM module (verified via
`WebAssembly.validate()` in the test suite). See "On WASM compilation"
below for why this is metadata-bundling rather than logic compilation.

**Package** -- zips everything into a `.tandem` artifact matching the
protocol doc's layout: `manifest.json`, `tasks/*.wasm`, `graph.json`,
`hashes.json`.

**Upload** -- POSTs the artifact to the server as `multipart/form-data`.
See "Transfer mechanism" below.

---

## On WASM compilation (read this before assuming more than is built)

There is no general AOT Python-to-native-WASM compiler integrated here,
and there isn't a mature open-source one to integrate. What exists for
running real Python inside WASM is Pyodide -- a full CPython build
targeting WASM -- not a translator from arbitrary Python source into
WASM instructions.

So "compiling to WASM" for Python tasks, today, means: **package the
metadata + source as data inside a real `.wasm` module**, using a
minimal hand-written WASM binary (one memory, one data segment, four
exported i32 globals giving byte offsets/lengths for the metadata and
source blobs). A node loading this module is expected to read the
globals, slice the bytes out of memory, and hand the source string off
to an embedded Pyodide interpreter to actually execute it. That
interpreter integration is **node-side**, out of scope for this CLI.

This keeps the artifact format honest -- every task really does ship a
valid `.wasm` file, satisfying the "WASM artifact" contract from the
protocol doc -- without overclaiming that Python got compiled to native
WASM bytecode.

Other languages (Rust, Go, C++, Java, TypeScript) are registered as
**stub backends** (`src/backends/stubs.ts`) -- detected by the scanner,
reported in build output, but compilation throws a clear "not
implemented yet" error naming the planned toolchain (e.g. `rustc
--target wasm32-unknown-unknown` for Rust, which -- unlike Python --
really would produce native WASM instructions, since Rust has a mature
wasm32 backend).

Adding a language: implement `CompilerBackend` (see
`src/backends/types.ts`), register it in `src/backends/registry.ts`. No
other CLI code needs to change.

---

## Transfer mechanism: multipart/form-data POST

The CLI uploads via a single `multipart/form-data` POST containing the
artifact as a binary file part, plus project name/version/hash as
companion text fields.

Why this over the alternatives (also documented inline in
`src/core/upload.ts`):

- **vs. base64-in-JSON**: avoids ~33% size inflation and full-string
  buffering of binary data on both ends. Matters once artifacts carry
  bundled immutable data (model weights, lookup tables) that can be MBs.
- **vs. raw octet-stream POST**: multipart still lets you send metadata
  (hash, version) alongside the bytes in one request without inventing
  custom headers for everything.
- **vs. gRPC streaming**: the eventual right answer at scale (proper
  backpressure, bidirectional progress), but it's a bigger commitment
  (server has to speak gRPC, schema versioning) that doesn't make sense
  before the server's transport layer is even decided.
- **vs. presigned-URL upload** (ask server for a short-lived S3-style
  PUT URL, upload directly to object storage): this is the right call
  once artifacts get large or upload volume is high, since it keeps big
  binary transfer off the application server entirely. It's a drop-in
  swap later -- `uploadArtifact()`'s signature doesn't need to change,
  just what happens inside it.

multipart/form-data is the right starting point: simple, supported by
literally every HTTP framework, and a one-line internal swap away from
presigned uploads later.

---

## Server URL

Hardcoded constant for now (`src/core/config.ts`):

```ts
export const DEFAULT_SERVER_URL = "https://api.tandem.dev";
```

Override with the `TANDEM_SERVER_URL` environment variable or the
`--server` flag -- both already wired up, since they cost nothing now
and are immediately useful for pointing at a local dev server.

**For production**, the recommended resolution order (not yet
implemented, see the TODO comment in `config.ts`) is the standard CLI
pattern: `--server` flag > `TANDEM_SERVER_URL` env var > a
`.tandemrc`/`tandem.config.json` in the project root > this constant as
the final fallback. This wasn't built out further because there's no
real server to route between yet -- wiring up a resolution chain with
nothing meaningful to resolve to would be speculative.

---

## Usage

```bash
npm install
npm run build

# Scan, validate, compile, package
node dist/index.js build \
  --path ./my-project \
  --out ./build.tandem \
  --name my-project \
  --python-sdk-path ../sdk/python-sdk

# Upload a built artifact
node dist/index.js upload ./build.tandem --name my-project

# Both in one step
node dist/index.js deploy --path ./my-project --python-sdk-path ../sdk/python-sdk
```

`--python-sdk-path` is added to `PYTHONPATH` for the validation step, so
`import tandem` resolves to the SDK in this repo without it being
formally installed.

If `python3` isn't on `PATH`, or the `tandem` package can't be
imported, validation is skipped with a warning rather than silently
reporting false success.

## Tests

```bash
npx vitest run
```

Covers: the WASM metadata-carrier builder (structural validity via
`WebAssembly.validate()`, round-trip data recovery, empty-source edge
case) and the scanner (compute/split detection, immutable bundle
detection, non-Python language detection without crashing).

---

## Server task-splitting design notes

A few things worth flagging while designing how the server splits and
schedules work, since they fell out of building the CLI side:

**Independence is enforced client-side, but the server should not trust
it blindly.** The CLI's build fails if validation fails -- but a
malicious or buggy client could skip the CLI and upload a hand-crafted
artifact. If the server ever runs untrusted code from arbitrary
uploaders (not just your own CLI), it needs its own sandboxing
independent of the "independence" contract; the contract optimizes for
*safe parallelization*, not *security isolation*. Worth deciding now
whether nodes run in a sandboxed runtime regardless of what the
manifest claims.

**The manifest's `split` hints are produced by a regex/heuristic
extraction on the TypeScript side, not the SDK's runtime values.** The
scanner reads `batch=3, timeout_ms=50` out of source text. If a project
computes these values dynamically (e.g. `batch=config.BATCH_SIZE`),
the scanner can't resolve them and currently falls back to defaults
silently. The server should treat manifest split hints as *hints*, not
guarantees, and probably wants a way for the real value to be confirmed
at runtime (e.g. the node reports back what batch size it actually saw)
rather than trusting the static manifest number for capacity planning.

**Chunking via `tandem.split` is synchronous and blocking from the
caller's perspective; batching via `@tandem.compute` is async-from-the-
caller's-thread but still blocking overall.** Neither has a "fire and
never wait" mode yet -- that's `@tandem.async`/`@tandem.deferred` from
the broader protocol doc, not implemented in the SDK yet. When you get
to the server's dispatch logic, compute/split jobs are best modeled as
synchronous RPC-style jobs (client connection stays open, server streams
back the result), whereas async/deferred jobs need the job-queue +
result-store model described in the protocol doc's section 9. These are
fundamentally different server code paths, not variations of the same
one -- worth keeping that split explicit in the server's architecture
rather than trying to unify them early.

**Hash-based integrity matters more once nodes can be untrusted.** The
CLI already computes and ships a SHA-256 per task (in `manifest.json`
and `hashes.json`) plus a whole-artifact hash on upload. The server
should verify these on receipt and again before dispatching to a node,
so a compromised or corrupted artifact can't silently execute different
code than what passed validation.
