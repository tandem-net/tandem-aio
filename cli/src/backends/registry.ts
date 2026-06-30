import type { CompilerBackend } from "./types.js";
import type { SupportedLanguage } from "../types/manifest.js";
import { PythonBackend } from "./python.js";
import { makeStubBackends } from "./stubs.js";

/**
 * Registry of all known backends, implemented or not. The scanner uses
 * this to map a discovered source file extension to a backend, and the
 * compile step uses it to find the right one to invoke.
 *
 * Adding a new language: write a CompilerBackend implementation, add it
 * here. No other CLI code needs to change -- this mirrors the
 * extensibility guarantee from the design doc.
 */
export class BackendRegistry {
  private readonly backends: CompilerBackend[];

  constructor(backends: CompilerBackend[]) {
    this.backends = backends;
  }

  static withDefaults(): BackendRegistry {
    return new BackendRegistry([new PythonBackend(), ...makeStubBackends()]);
  }

  byExtension(ext: string): CompilerBackend | undefined {
    const normalized = ext.replace(/^\./, "").toLowerCase();
    return this.backends.find((b) => b.extensions.includes(normalized));
  }

  byLanguage(language: SupportedLanguage): CompilerBackend | undefined {
    return this.backends.find((b) => b.language === language);
  }

  all(): CompilerBackend[] {
    return [...this.backends];
  }

  implementedLanguages(): SupportedLanguage[] {
    return this.backends.filter((b) => b.isImplemented()).map((b) => b.language);
  }
}
