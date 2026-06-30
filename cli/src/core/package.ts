import { createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";
import AdmZip from "adm-zip";
import type { CompiledTask, Manifest, ManifestTaskEntry } from "../types/manifest.js";

const CLI_VERSION = "0.1.0";

export interface PackageOptions {
  projectName: string;
  projectVersion: string;
  outputPath: string;
}

export async function packageArtifact(
  compiledTasks: CompiledTask[],
  opts: PackageOptions,
): Promise<{ manifest: Manifest; outputPath: string }> {
  const zip = new AdmZip();

  const manifestTasks: ManifestTaskEntry[] = compiledTasks.map((ct) => ({
    name: ct.spec.name,
    wasm: ct.wasmPath,
    hash: ct.hash,
    language: ct.spec.language,
    executionClass: ct.spec.executionClass,
    split: ct.spec.split,
    immutableBundles: ct.spec.immutableBundles,
    memoryMb: ct.spec.config.memory,
    timeoutMs: ct.spec.config.timeout,
  }));

  const manifest: Manifest = {
    name: opts.projectName,
    version: opts.projectVersion,
    tandemCliVersion: CLI_VERSION,
    createdAt: new Date().toISOString(),
    tasks: manifestTasks,
  };

  zip.addFile("manifest.json", Buffer.from(JSON.stringify(manifest, null, 2), "utf-8"));

  for (const task of compiledTasks) {
    zip.addFile(task.wasmPath, Buffer.from(task.bytes));
  }

  // graph.json placeholder -- populated once pipeline dependency
  // resolution exists. Always written, even if empty, so the artifact
  // shape matches the protocol doc's package layout.
  zip.addFile(
    "graph.json",
    Buffer.from(JSON.stringify({ pipeline_stages: [] }, null, 2), "utf-8"),
  );

  // hashes.json -- per-task content hash, duplicated here (also in
  // manifest entries) for tooling that wants a flat hash list without
  // parsing the full manifest.
  const hashes: Record<string, string> = {};
  for (const task of compiledTasks) {
    hashes[task.spec.name] = task.hash;
  }
  zip.addFile("hashes.json", Buffer.from(JSON.stringify(hashes, null, 2), "utf-8"));

  const buffer = zip.toBuffer();
  await writeFile(opts.outputPath, buffer);

  return { manifest, outputPath: opts.outputPath };
}

export function hashBytes(bytes: Uint8Array): string {
  return createHash("sha256").update(bytes).digest("hex");
}
