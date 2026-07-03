/**
 * Core type definitions for the Tandem build artifact.
 *
 * These mirror the manifest format described in the Tandem protocol doc
 * (split_hints, execution_class, immutable_bundles, etc). The CLI's job
 * is to discover tasks, validate them, and emit a manifest.json shaped
 * like this -- plus the actual WASM-runnable payload for each task.
 */

export type ExecutionClass = "compute" | "split" | "serve" | "scheduled";

export type SplitStrategy =
  | "data_parallel"
  | "pipeline"
  | "replicated"
  | "single";

/** Per-task split configuration, written by the CLI, may be overridden by the server at dispatch time. */
export interface SplitHints {
  strategy: SplitStrategy;
  /** For @tandem.compute(batch, timeout_ms) tasks. */
  batchSize?: number;
  timeoutMs?: number;
  /** For tandem.split(runnable, chunk) tasks. */
  chunkSize?: number;
  maxShards?: number;
  minShardSize?: number;
  reducer?: string;
  retryOnShardFailure?: boolean;
  maxRetriesPerShard?: number;
  replicas?: number;
}

/** A single task discovered in the project, in the SDK's universal JSON schema. */
export interface TaskSpec {
  name: string;
  entry: string;
  language: SupportedLanguage;
  executionClass: ExecutionClass;
  config: {
    timeout: number;
    memory: number;
  };
  split: SplitHints;
  /** Names of module-level variables this task reads, declared immutable in its source module. */
  immutableBundles: string[];
  /** Populated after the validator runs. */
  validated: boolean;
  validationErrors: string[];
}

export type SupportedLanguage =
  | "python"
  | "typescript"
  | "javascript"
  | "rust"
  | "go"
  | "java"
  | "cpp";

/** What the CLI packages for one task: metadata + whatever the backend produced as its runnable payload. */
export interface CompiledTask {
  spec: TaskSpec;
  /** Relative path, inside the artifact, to the runnable payload (e.g. tasks/foo.wasm or tasks/foo.tandem-py.wasm). */
  wasmPath: string;
  /** SHA-256 of the payload, used for integrity checking and content-addressing. */
  hash: string;
  /** Bytes of the actual payload, held in memory until packaging writes it to disk. */
  bytes: Uint8Array;
}

/** manifest.json -- the artifact's top-level descriptor. */
export interface Manifest {
  name: string;
  version: string;
  tandemCliVersion: string;
  createdAt: string;
  tasks: ManifestTaskEntry[];
}

export interface ManifestTaskEntry {
  name: string;
  wasm: string;
  hash: string;
  language: SupportedLanguage;
  executionClass: ExecutionClass;
  split: SplitHints;
  immutableBundles: string[];
  memoryMb: number;
  timeoutMs: number;
}
