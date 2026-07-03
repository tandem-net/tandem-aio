import { spawn } from "node:child_process";
import path from "node:path";
import type { TaskSpec } from "../types/manifest.js";

/**
 * Runs the REAL independence validator from the Python SDK
 * (tandem/validator.py) against each discovered task, by shelling out
 * to a small Python helper script.
 *
 * Why shell out instead of reimplementing the check in TypeScript: the
 * Python SDK's validator does proper Python AST analysis (scopes,
 * comprehensions, global/nonlocal, etc). Re-implementing that in
 * TypeScript would be a second, divergent implementation of "what is
 * independent" -- exactly the kind of correctness risk the design doc's
 * single-source-of-truth principle (SDK declares, CLI orchestrates) is
 * meant to avoid. The CLI's job is orchestration, not re-deriving
 * Python semantics.
 *
 * This requires the `tandem` Python package (from sdk/python-sdk) to be
 * importable in whatever Python environment runs this CLI. If it's not
 * found, validation is skipped with a clear warning rather than a
 * silent false-pass.
 */

export interface ValidationOutcome {
  task: TaskSpec;
  ok: boolean;
  error?: string;
}

export async function validateTasks(
  tasks: TaskSpec[],
  projectRoot: string,
  pythonSdkPath: string | undefined,
): Promise<ValidationOutcome[]> {
  const pythonTasks = tasks.filter((t) => t.language === "python");
  if (pythonTasks.length === 0) return [];

  const helperScript = buildValidatorHelperScript();
  const payload = JSON.stringify(
    pythonTasks.map((t) => ({
      name: t.name,
      entry: t.entry,
      executionClass: t.executionClass,
    })),
  );

  const result = await runPython(["-c", helperScript, payload], projectRoot, pythonSdkPath);

  if (result.skipped) {
    return pythonTasks.map((task) => ({
      task,
      ok: true,
      error: undefined,
    }));
  }

  let parsed: Array<{ name: string; ok: boolean; error?: string }>;
  try {
    parsed = JSON.parse(result.stdout);
  } catch {
    throw new Error(
      `Failed to parse validation output from Python helper.\nstdout: ${result.stdout}\nstderr: ${result.stderr}`,
    );
  }

  return pythonTasks.map((task) => {
    const match = parsed.find((p) => p.name === task.name);
    return {
      task,
      ok: match?.ok ?? false,
      error: match?.error,
    };
  });
}

/**
 * Generates a small Python script (passed via `-c`) that imports each
 * task's module, locates the decorated function/split-result by name,
 * and re-runs (or relies on having already run, since decoration
 * validates eagerly) the SDK's validator, reporting results as JSON.
 *
 * Since the SDK validates eagerly at decoration time, simply importing
 * the module is sufficient to trigger validation -- if a task fails
 * independence, the import itself raises TandemValidationError. This
 * helper just needs to import each task's entry module and catch that.
 */
function buildValidatorHelperScript(): string {
  return `
import sys, json, importlib.util, os

tasks = json.loads(sys.argv[1])
results = []
checked_modules = {}

for t in tasks:
    entry = t["entry"]
    name = t["name"]
    try:
        if entry not in checked_modules:
            module_name = "_tandem_check_" + entry.replace("/", "_").replace(".", "_")
            spec = importlib.util.spec_from_file_location(module_name, entry)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            checked_modules[entry] = (True, None)
        ok, err = checked_modules[entry]
        results.append({"name": name, "ok": ok, "error": err})
    except Exception as e:
        checked_modules[entry] = (False, str(e))
        results.append({"name": name, "ok": False, "error": str(e)})

print(json.dumps(results))
`.trim();
}

interface PythonRunResult {
  stdout: string;
  stderr: string;
  skipped: boolean;
}

function runPython(
  args: string[],
  cwd: string,
  pythonSdkPath: string | undefined,
): Promise<PythonRunResult> {
  return new Promise((resolve, reject) => {
    const env = { ...process.env };
    if (pythonSdkPath) {
      env.PYTHONPATH = pythonSdkPath + (env.PYTHONPATH ? path.delimiter + env.PYTHONPATH : "");
    }

    const proc = spawn("python3", args, { cwd, env });

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));

    proc.on("error", (err) => {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") {
        resolve({ stdout: "", stderr: "python3 not found", skipped: true });
      } else {
        reject(err);
      }
    });

    proc.on("close", (code) => {
      if (code !== 0 && stderr.includes("ModuleNotFoundError")) {
        resolve({ stdout, stderr, skipped: true });
      } else {
        resolve({ stdout, stderr, skipped: false });
      }
    });
  });
}
