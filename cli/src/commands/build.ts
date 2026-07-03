import path from "node:path";
import chalk from "chalk";
import { scanProject } from "../core/scanner.js";
import { validateTasks } from "../core/validate.js";
import { packageArtifact, hashBytes } from "../core/package.js";
import { BackendRegistry } from "../backends/registry.js";
import type { CompiledTask } from "../types/manifest.js";

export interface BuildOptions {
  projectRoot: string;
  outputPath: string;
  projectName: string;
  projectVersion: string;
  pythonSdkPath?: string;
  skipValidation?: boolean;
}

export interface BuildResult {
  success: boolean;
  manifestPath?: string;
  taskCount: number;
  errors: string[];
}

export async function runBuild(opts: BuildOptions): Promise<BuildResult> {
  const errors: string[] = [];

  console.log(chalk.bold("Scanning project..."));
  const scan = await scanProject(opts.projectRoot);

  if (scan.tasks.length === 0) {
    console.log(chalk.yellow("No tandem tasks found."));
    if (scan.detectedLanguages.length > 0) {
      console.log(
        `  Detected source files for: ${scan.detectedLanguages.join(", ")}, but no @tandem.compute / tandem.split usage found.`,
      );
    }
    return { success: false, taskCount: 0, errors: ["No tasks found"] };
  }

  console.log(
    `  Found ${chalk.cyan(scan.tasks.length.toString())} task(s) across ${scan.detectedLanguages.length} language(s): ${scan.detectedLanguages.join(", ")}`,
  );

  const registry = BackendRegistry.withDefaults();
  reportUnimplementedLanguages(scan.detectedLanguages, registry);

  if (!opts.skipValidation) {
    console.log(chalk.bold("\nValidating split-independence..."));
    const outcomes = await validateTasks(scan.tasks, opts.projectRoot, opts.pythonSdkPath);

    let anyChecked = false;
    for (const outcome of outcomes) {
      anyChecked = true;
      if (outcome.ok) {
        console.log(`  ${chalk.green("✓")} ${outcome.task.name}`);
      } else {
        console.log(`  ${chalk.red("✗")} ${outcome.task.name}: ${outcome.error}`);
        errors.push(`${outcome.task.name}: ${outcome.error}`);
      }
    }

    if (!anyChecked) {
      console.log(chalk.dim("  (skipped -- python3 or the tandem package not found on PATH)"));
    }

    if (errors.length > 0) {
      console.log(chalk.bold.red(`\nBuild failed: ${errors.length} task(s) failed validation.`));
      return { success: false, taskCount: scan.tasks.length, errors };
    }
  }

  console.log(chalk.bold("\nCompiling tasks..."));
  const compiledTasks: CompiledTask[] = [];

  for (const task of scan.tasks) {
    const backend = registry.byLanguage(task.language);
    if (!backend || !backend.isImplemented()) {
      const msg = `No implemented backend for language "${task.language}" (task "${task.name}")`;
      console.log(`  ${chalk.red("✗")} ${task.name}: ${msg}`);
      errors.push(msg);
      continue;
    }

    try {
      const result = await backend.compile(task, opts.projectRoot);
      const hash = hashBytes(result.bytes);
      const wasmPath = `tasks/${task.name}.${result.extension}`;

      compiledTasks.push({ spec: task, wasmPath, hash, bytes: result.bytes });

      console.log(`  ${chalk.green("✓")} ${task.name} -> ${wasmPath} (${result.bytes.length} bytes)`);
      result.notes?.forEach((note) => console.log(chalk.dim(`      ${note}`)));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.log(`  ${chalk.red("✗")} ${task.name}: ${msg}`);
      errors.push(msg);
    }
  }

  if (errors.length > 0) {
    console.log(chalk.bold.red(`\nBuild failed: ${errors.length} task(s) failed to compile.`));
    return { success: false, taskCount: scan.tasks.length, errors };
  }

  console.log(chalk.bold("\nPackaging artifact..."));
  const { manifest, outputPath } = await packageArtifact(compiledTasks, {
    projectName: opts.projectName,
    projectVersion: opts.projectVersion,
    outputPath: opts.outputPath,
  });

  console.log(`  ${chalk.green("✓")} Wrote ${path.relative(process.cwd(), outputPath)}`);
  console.log(chalk.dim(`      ${manifest.tasks.length} task(s), manifest v${manifest.tandemCliVersion}`));

  return { success: true, manifestPath: outputPath, taskCount: scan.tasks.length, errors: [] };
}

function reportUnimplementedLanguages(detected: string[], registry: BackendRegistry): void {
  const implemented = new Set(registry.implementedLanguages());
  const unimplementedDetected = detected.filter((lang) => !implemented.has(lang as never));
  if (unimplementedDetected.length > 0) {
    console.log(
      chalk.yellow(
        `  Note: found source files for ${unimplementedDetected.join(", ")}, but no compiler backend is implemented yet for these languages. See backends/stubs.ts.`,
      ),
    );
  }
}
