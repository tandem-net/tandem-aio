import { readFile } from "node:fs/promises";
import path from "node:path";
import fg from "fast-glob";
import type { ExecutionClass, SplitHints, SupportedLanguage, TaskSpec } from "../types/manifest.js";

/**
 * Scans a Python project for tandem task definitions and extracts the
 * metadata the SDK would have produced for each one.
 *
 * NOTE ON IMPLEMENTATION: this is regex/line-based extraction, not a
 * real Python AST parser. The Python SDK itself (tandem/validator.py)
 * does the actual AST-based independence validation at decoration time,
 * in-process, in Python. The CLI does not re-implement a Python parser
 * in TypeScript -- that would be both redundant and a correctness risk
 * (two independent implementations of "what counts as independent"
 * drifting apart).
 *
 * Instead, the CLI's scanner does light source inspection to (a) find
 * task definitions and (b) build the manifest's task list and split
 * hints, and DEFERS to a Python-side helper for full validation -- see
 * runPythonValidation() in validate.ts, which actually imports the
 * Python SDK and lets its real validator do the work. This scanner's
 * job is discovery, not enforcement.
 */

const DEFAULT_TIMEOUT_MS = 30_000;
const DEFAULT_MEMORY_MB = 128;

export interface ScanResult {
  tasks: TaskSpec[];
  /** Files that matched a source extension but produced no detected tasks. */
  skippedFiles: string[];
  /** Languages detected in the project that the CLI found source files for. */
  detectedLanguages: SupportedLanguage[];
}

const LANGUAGE_EXTENSIONS: Record<SupportedLanguage, string[]> = {
  python: ["py"],
  typescript: ["ts"],
  javascript: ["js", "mjs"],
  rust: ["rs"],
  go: ["go"],
  java: ["java"],
  cpp: ["cpp", "cc", "cxx"],
};

function languageForExtension(ext: string): SupportedLanguage | undefined {
  const normalized = ext.replace(/^\./, "").toLowerCase();
  for (const [lang, exts] of Object.entries(LANGUAGE_EXTENSIONS)) {
    if (exts.includes(normalized)) return lang as SupportedLanguage;
  }
  return undefined;
}

export async function scanProject(projectRoot: string): Promise<ScanResult> {
  const allExtensions = Object.values(LANGUAGE_EXTENSIONS).flat();
  const pattern = `**/*.{${allExtensions.join(",")}}`;

  const files = await fg(pattern, {
    cwd: projectRoot,
    ignore: ["**/node_modules/**", "**/.git/**", "**/__pycache__/**", "**/dist/**", "**/.venv/**", "**/venv/**"],
  });

  const tasks: TaskSpec[] = [];
  const skippedFiles: string[] = [];
  const detectedLanguages = new Set<SupportedLanguage>();

  for (const relPath of files) {
    const ext = path.extname(relPath);
    const language = languageForExtension(ext);
    if (!language) continue;

    detectedLanguages.add(language);

    if (language !== "python") {
      // Only Python extraction is implemented today. Other languages
      // are recorded as detected (so build output can say "found 3 .rs
      // files, rust backend not implemented yet") without attempting
      // (and failing) task extraction.
      continue;
    }

    const absPath = path.join(projectRoot, relPath);
    const source = await readFile(absPath, "utf-8");
    const found = extractPythonTasks(source, relPath);

    if (found.length === 0) {
      skippedFiles.push(relPath);
    } else {
      tasks.push(...found);
    }
  }

  return { tasks, skippedFiles, detectedLanguages: [...detectedLanguages] };
}

/**
 * Extracts @tandem.compute(...) and `name = tandem.split(fn, ...)`
 * task definitions from a Python source file's text.
 *
 * This is intentionally simple line-based extraction covering the
 * documented call shapes:
 *
 *   @tandem.compute()
 *   @tandem.compute(batch=3, timeout_ms=50)
 *   def foo(x): ...
 *
 *   goo = tandem.split(foo, 5)
 *   goo = tandem.split(foo, chunk=5)
 *
 * It does not attempt to resolve indirect references, dynamic
 * decoration, or anything requiring real evaluation -- that mirrors the
 * SDK's own validator limitations (see python-sdk/README.md "Known
 * limitations"), and is fine for the scanner's discovery purpose since
 * actual independence enforcement happens in Python, not here.
 */
function extractPythonTasks(source: string, relPath: string): TaskSpec[] {
  const tasks: TaskSpec[] = [];
  const lines = source.split("\n");

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    const computeMatch = line.match(/@tandem\.compute\s*\(([^)]*)\)/);
    if (computeMatch) {
      const nextDef = findNextDef(lines, i + 1);
      if (nextDef) {
        const args = parseKwargs(computeMatch[1]);
        tasks.push(
          buildTaskSpec({
            name: nextDef.name,
            relPath,
            executionClass: "compute",
            split: {
              strategy: "single",
              batchSize: numArg(args, "batch", 0, 1),
              timeoutMs: numArg(args, "timeout_ms", 1, 50),
            },
            immutableBundles: findImmutableReads(source, nextDef.name),
          }),
        );
      }
      continue;
    }

    const splitMatch = line.match(/^\s*(\w+)\s*=\s*tandem\.split\s*\(\s*(\w+)\s*(?:,\s*(?:chunk\s*=\s*)?(\d+))?\s*\)/);
    if (splitMatch) {
      const [, boundName, sourceFn, chunkStr] = splitMatch;
      tasks.push(
        buildTaskSpec({
          name: boundName,
          relPath,
          executionClass: "split",
          split: {
            strategy: "data_parallel",
            chunkSize: chunkStr ? parseInt(chunkStr, 10) : 1,
          },
          immutableBundles: findImmutableReads(source, sourceFn),
        }),
      );
    }
  }

  return tasks;
}

function findNextDef(lines: string[], startIdx: number): { name: string } | undefined {
  for (let i = startIdx; i < Math.min(startIdx + 5, lines.length); i++) {
    const m = lines[i].match(/^\s*(?:async\s+)?def\s+(\w+)\s*\(/);
    if (m) return { name: m[1] };
    // Allow stacking multiple decorators before hitting `def`.
    if (!lines[i].trim().startsWith("@") && lines[i].trim() !== "") break;
  }
  return undefined;
}

function parseKwargs(argString: string): Map<string, string> {
  const result = new Map<string, string>();
  const trimmed = argString.trim();
  if (!trimmed) return result;
  const parts = trimmed.split(",").map((p) => p.trim());
  parts.forEach((part, idx) => {
    if (!part) return;
    const eq = part.indexOf("=");
    if (eq === -1) {
      // positional arg
      result.set(`__pos${idx}`, part.trim());
    } else {
      result.set(part.slice(0, eq).trim(), part.slice(eq + 1).trim());
    }
  });
  return result;
}

function numArg(args: Map<string, string>, name: string, posIndex: number, fallback: number): number {
  const named = args.get(name);
  if (named !== undefined) return parseInt(named, 10);
  const positional = args.get(`__pos${posIndex}`);
  if (positional !== undefined) return parseInt(positional, 10);
  return fallback;
}

/**
 * Best-effort scan for which `tandem.immutable(...)`-declared names a
 * given function body reads. This is a coarse heuristic (regex over the
 * function's body text), not real scope analysis -- the SDK's own AST
 * validator is the source of truth; this is purely for populating the
 * manifest's `immutableBundles` list for visibility.
 */
function findImmutableReads(source: string, functionName: string): string[] {
  const immutableNames = new Set<string>();
  const immutablePattern = /^\s*(\w+)\s*=\s*tandem\.immutable\s*\(/gm;
  let m: RegExpExecArray | null;
  while ((m = immutablePattern.exec(source)) !== null) {
    immutableNames.add(m[1]);
  }
  if (immutableNames.size === 0) return [];

  const bodyMatch = source.match(
    new RegExp(`def\\s+${functionName}\\s*\\([^)]*\\)[^:]*:([\\s\\S]*?)(?=\\n\\S|\\n*$)`),
  );
  if (!bodyMatch) return [];
  const body = bodyMatch[1];

  return [...immutableNames].filter((name) => new RegExp(`\\b${name}\\b`).test(body));
}

function buildTaskSpec(opts: {
  name: string;
  relPath: string;
  executionClass: ExecutionClass;
  split: SplitHints;
  immutableBundles: string[];
}): TaskSpec {
  return {
    name: opts.name,
    entry: opts.relPath,
    language: "python",
    executionClass: opts.executionClass,
    config: {
      timeout: DEFAULT_TIMEOUT_MS,
      memory: DEFAULT_MEMORY_MB,
    },
    split: opts.split,
    immutableBundles: opts.immutableBundles,
    validated: false,
    validationErrors: [],
  };
}
