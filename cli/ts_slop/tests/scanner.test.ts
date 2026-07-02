import { describe, it, expect } from "vitest";
import { scanProject } from "../src/core/scanner.js";
import { writeFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

async function withTempProject(files: Record<string, string>, run: (dir: string) => Promise<void>) {
  const dir = await mkdtemp(path.join(tmpdir(), "tandem-scan-"));
  for (const [name, content] of Object.entries(files)) {
    await writeFile(path.join(dir, name), content, "utf-8");
  }
  try {
    await run(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

describe("scanProject", () => {
  it("detects @tandem.compute tasks with batch and timeout_ms", async () => {
    await withTempProject(
      {
        "tasks.py": [
          "import tandem",
          "",
          "@tandem.compute(batch=3, timeout_ms=50)",
          "def foo(x):",
          "    return x * 2",
          "",
        ].join("\n"),
      },
      async (dir) => {
        const result = await scanProject(dir);
        expect(result.tasks).toHaveLength(1);
        expect(result.tasks[0].name).toBe("foo");
        expect(result.tasks[0].executionClass).toBe("compute");
        expect(result.tasks[0].split.batchSize).toBe(3);
        expect(result.tasks[0].split.timeoutMs).toBe(50);
      },
    );
  });

  it("detects tandem.split bindings with chunk size", async () => {
    await withTempProject(
      {
        "tasks.py": [
          "import tandem",
          "",
          "def bar(x):",
          "    return x + 3",
          "",
          "goo = tandem.split(bar, 5)",
          "",
        ].join("\n"),
      },
      async (dir) => {
        const result = await scanProject(dir);
        expect(result.tasks).toHaveLength(1);
        expect(result.tasks[0].name).toBe("goo");
        expect(result.tasks[0].executionClass).toBe("split");
        expect(result.tasks[0].split.chunkSize).toBe(5);
      },
    );
  });

  it("finds immutable bundle names referenced inside a task body", async () => {
    await withTempProject(
      {
        "tasks.py": [
          "import tandem",
          "",
          "NUM = tandem.immutable(67)",
          "",
          "@tandem.compute()",
          "def foo(x):",
          "    return NUM + x",
          "",
        ].join("\n"),
      },
      async (dir) => {
        const result = await scanProject(dir);
        expect(result.tasks[0].immutableBundles).toEqual(["NUM"]);
      },
    );
  });

  it("does not crash on files with no tandem usage and reports them as skipped", async () => {
    await withTempProject(
      {
        "plain.py": "def add(a, b):\n    return a + b\n",
      },
      async (dir) => {
        const result = await scanProject(dir);
        expect(result.tasks).toHaveLength(0);
        expect(result.skippedFiles).toContain("plain.py");
      },
    );
  });

  it("detects non-python source files without attempting extraction", async () => {
    await withTempProject(
      {
        "main.rs": "fn main() {}\n",
      },
      async (dir) => {
        const result = await scanProject(dir);
        expect(result.tasks).toHaveLength(0);
        expect(result.detectedLanguages).toContain("rust");
      },
    );
  });
});
