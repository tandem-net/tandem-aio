import type { BackendCompileResult, CompilerBackend } from "./types.js";
import type { SupportedLanguage, TaskSpec } from "../types/manifest.js";

/**
 * Stub backend for languages whose toolchain isn't wired up yet.
 *
 * Per the design doc's extensibility section, adding a new language
 * should only require: an SDK wrapper + a CLI backend, no server
 * changes. This class is the "no CLI backend yet" placeholder -- it
 * detects the language so the scanner can report it accurately, but
 * refuses to compile with a clear error pointing at what's missing.
 */
export class UnimplementedBackend implements CompilerBackend {
  constructor(
    readonly language: SupportedLanguage,
    readonly extensions: string[],
    private readonly toolchainNote: string,
  ) {}

  isImplemented(): boolean {
    return false;
  }

  async compile(task: TaskSpec): Promise<BackendCompileResult> {
    throw new Error(
      `No compiler backend implemented yet for language "${this.language}" ` +
        `(task "${task.name}"). ${this.toolchainNote}`,
    );
  }
}

export function makeStubBackends(): CompilerBackend[] {
  return [
    new UnimplementedBackend(
      "rust",
      ["rs"],
      "Planned toolchain: rustc --target wasm32-unknown-unknown (or wasm32-wasi). Rust compiles to real native WASM, unlike the Python metadata-carrier approach.",
    ),
    new UnimplementedBackend(
      "go",
      ["go"],
      "Planned toolchain: tinygo build -target=wasm.",
    ),
    new UnimplementedBackend(
      "cpp",
      ["cpp", "cc", "cxx"],
      "Planned toolchain: clang --target=wasm32 (or Emscripten for a fuller libc).",
    ),
    new UnimplementedBackend(
      "java",
      ["java"],
      "Planned toolchain: TeaVM or CheerpJ to compile JVM bytecode to WASM.",
    ),
    new UnimplementedBackend(
      "typescript",
      ["ts"],
      "Planned toolchain: AssemblyScript subset compilation, or a metadata-carrier approach similar to Python's via a JS engine embedded on the node.",
    ),
    new UnimplementedBackend(
      "javascript",
      ["js", "mjs"],
      "Planned toolchain: same as typescript -- likely a metadata-carrier + embedded JS engine on the node, similar to the Python approach.",
    ),
  ];
}
