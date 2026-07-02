import type { SupportedLanguage, TaskSpec } from "../types/manifest.js";

/**
 * Result of compiling a single task to its runnable WASM payload.
 */
export interface BackendCompileResult {
  /** Raw bytes of the artifact to embed in the .tandem package for this task. */
  bytes: Uint8Array;
  /** File extension used for the payload inside tasks/, e.g. "wasm". */
  extension: string;
  /** Free-form notes the backend wants surfaced in build output (e.g. "embedded Pyodide runtime"). */
  notes?: string[];
}

/**
 * A CompilerBackend is responsible for turning ONE task's source into a
 * runnable WASM payload. This mirrors the CompilerBackend interface from
 * the original Tandem design doc:
 *
 *   interface CompilerBackend {
 *     language: string;
 *     detect(project): boolean;
 *     compile(task): Promise<WasmArtifact>;
 *   }
 *
 * `detect` lets the CLI's scanner figure out which backend owns a given
 * source file without hardcoding extension checks everywhere.
 */
export interface CompilerBackend {
  readonly language: SupportedLanguage;

  /** File extensions (without dot) this backend claims, e.g. ["py"]. */
  readonly extensions: string[];

  /**
   * Whether this backend can compile the given task right now. A
   * backend that has no toolchain wired up yet (e.g. Rust, until rustc
   * wasm32 is integrated) should return false here and the scanner will
   * report it as "detected but not yet supported" rather than silently
   * skipping it.
   */
  isImplemented(): boolean;

  /** Compile one task to a WASM-runnable payload. */
  compile(task: TaskSpec, projectRoot: string): Promise<BackendCompileResult>;
}
