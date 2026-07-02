import { describe, it, expect } from "vitest";
import { PythonBackend } from "../src/backends/python.js";
import type { TaskSpec } from "../src/types/manifest.js";
import { writeFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

function makeTask(overrides: Partial<TaskSpec> = {}): TaskSpec {
  return {
    name: "foo",
    entry: "tasks.py",
    language: "python",
    executionClass: "compute",
    config: { timeout: 30000, memory: 128 },
    split: { strategy: "single", batchSize: 1, timeoutMs: 50 },
    immutableBundles: [],
    validated: true,
    validationErrors: [],
    ...overrides,
  };
}

describe("PythonBackend", () => {
  it("produces structurally valid WASM", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "tandem-test-"));
    const entry = "tasks.py";
    const source = "def foo(x):\n    return x * 2\n";
    await writeFile(path.join(dir, entry), source, "utf-8");

    const backend = new PythonBackend();
    const result = await backend.compile(makeTask({ entry }), dir);

    expect(WebAssembly.validate(result.bytes)).toBe(true);

    await rm(dir, { recursive: true, force: true });
  });

  it("embeds metadata and source recoverably via exported globals", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "tandem-test-"));
    const entry = "tasks.py";
    const source = "def foo(x):\n    return x * 2\n";
    await writeFile(path.join(dir, entry), source, "utf-8");

    const backend = new PythonBackend();
    const task = makeTask({ entry, immutableBundles: ["NUM"] });
    const result = await backend.compile(task, dir);

    const module = await WebAssembly.instantiate(result.bytes);
    const exports = module.instance.exports as Record<string, WebAssembly.Global> & {
      memory: WebAssembly.Memory;
    };

    const mem = new Uint8Array(exports.memory.buffer);
    const metaOffset = (exports.meta_offset as unknown as WebAssembly.Global).value as number;
    const metaLen = (exports.meta_len as unknown as WebAssembly.Global).value as number;
    const srcOffset = (exports.src_offset as unknown as WebAssembly.Global).value as number;
    const srcLen = (exports.src_len as unknown as WebAssembly.Global).value as number;

    const metaJson = Buffer.from(mem.slice(metaOffset, metaOffset + metaLen)).toString("utf-8");
    const extractedSource = Buffer.from(mem.slice(srcOffset, srcOffset + srcLen)).toString("utf-8");

    const meta = JSON.parse(metaJson);
    expect(meta.name).toBe("foo");
    expect(meta.immutableBundles).toEqual(["NUM"]);
    expect(extractedSource).toBe(source);

    await rm(dir, { recursive: true, force: true });
  });

  it("handles empty source and metadata without producing invalid WASM", async () => {
    const dir = await mkdtemp(path.join(tmpdir(), "tandem-test-"));
    const entry = "empty.py";
    await writeFile(path.join(dir, entry), "", "utf-8");

    const backend = new PythonBackend();
    const result = await backend.compile(makeTask({ entry, immutableBundles: [] }), dir);

    expect(WebAssembly.validate(result.bytes)).toBe(true);

    await rm(dir, { recursive: true, force: true });
  });

  it("reports isImplemented() as true", () => {
    expect(new PythonBackend().isImplemented()).toBe(true);
  });
});
