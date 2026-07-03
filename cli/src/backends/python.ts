import { readFile } from "node:fs/promises";
import path from "node:path";
import type { BackendCompileResult, CompilerBackend } from "./types.js";
import type { TaskSpec } from "../types/manifest.js";

/**
 * Python backend.
 *
 * IMPORTANT, READ THIS: there is no AOT Python -> native-WASM toolchain
 * wired up here. That doesn't really exist in a general form today --
 * Pyodide / Pyodide-CPython-on-WASM is the realistic path for running
 * arbitrary Python inside a WASM sandbox, and even that ships a whole
 * CPython runtime compiled to WASM, not a translation of your specific
 * function into native WASM bytecode.
 *
 * So what this backend actually does -- and what "bundling SDK metadata
 * into wasm" means in practice for Python right now -- is:
 *
 *   1. Read the task's source file.
 *   2. Build the task metadata JSON (the SDK's universal schema: name,
 *      entry, language, config, split hints, immutable bundle names).
 *   3. Package BOTH the metadata and the raw Python source as a small
 *      WASM module's data section, using a minimal hand-rolled WASM
 *      binary (a single passive data segment + a no-op start function).
 *      This produces a real, valid .wasm file that nodes can load, but
 *      its job is to CARRY the metadata + source, not to execute Python
 *      logic via WASM instructions.
 *   4. The eventual node runtime is expected to: load this module,
 *      pull the embedded JSON + source back out of its data segment,
 *      and hand the source off to an embedded Pyodide (CPython-on-WASM)
 *      interpreter to actually run it. That interpreter integration is
 *      a node-side concern, not something this CLI backend builds.
 *
 * This keeps the artifact format honest: every .tandem task ships a
 * real .wasm file (so the "WASM artifact" contract in the protocol doc
 * holds), without pretending Python source got compiled to native WASM
 * instructions, which would be a false claim.
 */
export class PythonBackend implements CompilerBackend {
  readonly language = "python" as const;
  readonly extensions = ["py"];

  isImplemented(): boolean {
    return true;
  }

  async compile(task: TaskSpec, projectRoot: string): Promise<BackendCompileResult> {
    const sourcePath = path.join(projectRoot, task.entry);
    const source = await readFile(sourcePath, "utf-8");

    const metadata = {
      name: task.name,
      entry: task.entry,
      language: task.language,
      executionClass: task.executionClass,
      config: task.config,
      split: task.split,
      immutableBundles: task.immutableBundles,
    };

    const wasmBytes = buildMetadataCarrierWasm({
      metadataJson: JSON.stringify(metadata),
      sourceCode: source,
    });

    return {
      bytes: wasmBytes,
      extension: "wasm",
      notes: [
        "Python backend bundles source + metadata into a WASM data-carrier module.",
        "No AOT Python compilation occurs; execution is expected to happen via a node-side Pyodide runtime that reads this module's data segments.",
      ],
    };
  }
}

/**
 * Builds a minimal, valid WASM binary module whose only purpose is to
 * carry two UTF-8 byte blobs (metadata JSON, then source code) inside a
 * passive data segment, plus exported i32 globals giving their byte
 * offsets/lengths so a host runtime can locate and slice them out of
 * linear memory after instantiation.
 *
 * This is hand-assembled (no wasm toolchain dependency) by emitting the
 * binary module format directly: magic number, version, then the
 * minimal set of sections needed (memory, data, global exports).
 *
 * Layout in linear memory (single page, 64KiB, grown if needed):
 *   [0 .. metaLen)                  -> metadata JSON bytes
 *   [metaLen .. metaLen+srcLen)     -> source code bytes
 *
 * Exported globals (all i32, immutable):
 *   "meta_offset", "meta_len", "src_offset", "src_len"
 */
function buildMetadataCarrierWasm(payload: { metadataJson: string; sourceCode: string }): Uint8Array {
  const metaBytes = Buffer.from(payload.metadataJson, "utf-8");
  const srcBytes = Buffer.from(payload.sourceCode, "utf-8");

  const metaOffset = 0;
  const metaLen = metaBytes.length;
  const srcOffset = metaLen;
  const srcLen = srcBytes.length;

  const totalDataBytes = metaLen + srcLen;
  const pageSize = 65536;
  const pagesNeeded = Math.max(1, Math.ceil(totalDataBytes / pageSize));

  const w = new WasmWriter();

  // -- magic + version --
  w.bytes([0x00, 0x61, 0x73, 0x6d]); // '\0asm'
  w.bytes([0x01, 0x00, 0x00, 0x00]); // version 1

  // -- Type section (id 1): one type () -> () --
  w.section(1, (s) => {
    s.uleb(1); // 1 type
    s.byte(0x60); // func type
    s.uleb(0); // 0 params
    s.uleb(0); // 0 results
  });

  // -- Function section (id 3): one function using type 0 --
  w.section(3, (s) => {
    s.uleb(1); // 1 function
    s.uleb(0); // type index 0
  });

  // -- Memory section (id 5): one memory, min = pagesNeeded pages --
  w.section(5, (s) => {
    s.uleb(1); // 1 memory
    s.byte(0x00); // limits: flags=0 (min only)
    s.uleb(pagesNeeded);
  });

  // -- Global section (id 6): four i32 immutable globals --
  w.section(6, (s) => {
    s.uleb(4); // 4 globals
    for (const value of [metaOffset, metaLen, srcOffset, srcLen]) {
      s.byte(0x7f); // valtype i32
      s.byte(0x00); // mutability: const
      s.byte(0x41); // i32.const
      s.sleb(value);
      s.byte(0x0b); // end
    }
  });

  // -- Export section (id 7): export _start, memory, + 4 globals by name --
  w.section(7, (s) => {
    const exportsList: Array<[string, number, number]> = [
      ["_start", 0x00, 0], // kind=func, index 0
      ["memory", 0x02, 0], // kind=memory, index 0
      ["meta_offset", 0x03, 0], // kind=global
      ["meta_len", 0x03, 1],
      ["src_offset", 0x03, 2],
      ["src_len", 0x03, 3],
    ];
    s.uleb(exportsList.length);
    for (const [name, kind, index] of exportsList) {
      s.name(name);
      s.byte(kind);
      s.uleb(index);
    }
  });

  // -- Code section (id 10): one function body (empty) --
  w.section(10, (s) => {
    s.uleb(1); // 1 body
    s.uleb(2); // body size = 2 bytes (1 byte local count, 1 byte end)
    s.uleb(0); // 0 local declarations
    s.byte(0x0b); // end
  });

  // -- Data section (id 11): one passive-free active data segment --
  w.section(11, (s) => {
    s.uleb(1); // 1 data segment
    s.byte(0x00); // active segment, memory index 0 implied
    // offset expr: i32.const 0, end
    s.byte(0x41);
    s.sleb(0);
    s.byte(0x0b);
    const combined = Buffer.concat([metaBytes, srcBytes]);
    s.uleb(combined.length);
    s.raw(combined);
  });

  return w.finish();
}

/** Tiny helper for emitting WASM binary sections without a dependency. */
class WasmWriter {
  private chunks: Buffer[] = [];

  bytes(arr: number[]): void {
    this.chunks.push(Buffer.from(arr));
  }

  raw(buf: Buffer): void {
    this.chunks.push(buf);
  }

  section(id: number, build: (s: SectionBuilder) => void): void {
    const builder = new SectionBuilder();
    build(builder);
    const body = builder.finish();
    this.chunks.push(Buffer.from([id]));
    this.chunks.push(uleb128(body.length));
    this.chunks.push(body);
  }

  finish(): Uint8Array {
    return new Uint8Array(Buffer.concat(this.chunks));
  }
}

class SectionBuilder {
  private chunks: Buffer[] = [];

  byte(b: number): void {
    this.chunks.push(Buffer.from([b & 0xff]));
  }

  uleb(value: number): void {
    this.chunks.push(uleb128(value));
  }

  sleb(value: number): void {
    this.chunks.push(sleb128(value));
  }

  raw(buf: Buffer): void {
    this.chunks.push(buf);
  }

  name(s: string): void {
    const buf = Buffer.from(s, "utf-8");
    this.uleb(buf.length);
    this.raw(buf);
  }

  finish(): Buffer {
    return Buffer.concat(this.chunks);
  }
}

function uleb128(value: number): Buffer {
  const bytes: number[] = [];
  let v = value;
  do {
    let byte = v & 0x7f;
    v >>>= 7;
    if (v !== 0) byte |= 0x80;
    bytes.push(byte);
  } while (v !== 0);
  return Buffer.from(bytes);
}

function sleb128(value: number): Buffer {
  const bytes: number[] = [];
  let v = value;
  let more = true;
  while (more) {
    let byte = v & 0x7f;
    v >>= 7;
    const signBitSet = (byte & 0x40) !== 0;
    if ((v === 0 && !signBitSet) || (v === -1 && signBitSet)) {
      more = false;
    } else {
      byte |= 0x80;
    }
    bytes.push(byte);
  }
  return Buffer.from(bytes);
}
