#!/usr/bin/env node
import path from "node:path";
import { Command } from "commander";
import chalk from "chalk";
import { runBuild } from "./commands/build.js";
import { runUpload } from "./commands/upload.js";
import { DEFAULT_SERVER_URL } from "./core/config.js";

const program = new Command();

program
  .name("tandem")
  .description("Tandem build CLI -- scans, validates, and packages tasks into a .tandem artifact")
  .version("0.1.0");

program
  .command("build")
  .description("Scan the project, validate task independence, compile, and package a .tandem artifact")
  .option("-p, --path <dir>", "project root to scan", ".")
  .option("-o, --out <file>", "output artifact path", "build.tandem")
  .option("-n, --name <name>", "project name", "tandem-project")
  .option("--project-version <version>", "project version", "0.1.0")
  .option("--python-sdk-path <dir>", "path to the tandem Python SDK, added to PYTHONPATH for validation")
  .option("--skip-validation", "skip the independence validation step (not recommended)", false)
  .action(async (options) => {
    const result = await runBuild({
      projectRoot: path.resolve(options.path),
      outputPath: path.resolve(options.out),
      projectName: options.name,
      projectVersion: options.projectVersion,
      pythonSdkPath: options.pythonSdkPath ? path.resolve(options.pythonSdkPath) : undefined,
      skipValidation: options.skipValidation,
    });

    if (!result.success) {
      process.exit(1);
    }
  });

program
  .command("upload")
  .description("Upload a built .tandem artifact to the server")
  .argument("<artifact>", "path to the .tandem artifact")
  .option("-n, --name <name>", "project name", "tandem-project")
  .option("--project-version <version>", "project version", "0.1.0")
  .option("--server <url>", `server URL (default: ${DEFAULT_SERVER_URL}, override with TANDEM_SERVER_URL env var)`)
  .action(async (artifact, options) => {
    const ok = await runUpload({
      artifactPath: path.resolve(artifact),
      projectName: options.name,
      projectVersion: options.projectVersion,
      serverUrl: options.server,
    });
    if (!ok) process.exit(1);
  });

program
  .command("deploy")
  .description("Build and upload in one step (build + upload)")
  .option("-p, --path <dir>", "project root to scan", ".")
  .option("-o, --out <file>", "output artifact path", "build.tandem")
  .option("-n, --name <name>", "project name", "tandem-project")
  .option("--project-version <version>", "project version", "0.1.0")
  .option("--python-sdk-path <dir>", "path to the tandem Python SDK, added to PYTHONPATH for validation")
  .option("--server <url>", `server URL (default: ${DEFAULT_SERVER_URL}, override with TANDEM_SERVER_URL env var)`)
  .action(async (options) => {
    const buildResult = await runBuild({
      projectRoot: path.resolve(options.path),
      outputPath: path.resolve(options.out),
      projectName: options.name,
      projectVersion: options.projectVersion,
      pythonSdkPath: options.pythonSdkPath ? path.resolve(options.pythonSdkPath) : undefined,
    });

    if (!buildResult.success || !buildResult.manifestPath) {
      process.exit(1);
    }

    console.log();
    const ok = await runUpload({
      artifactPath: buildResult.manifestPath,
      projectName: options.name,
      projectVersion: options.projectVersion,
      serverUrl: options.server,
    });
    if (!ok) process.exit(1);
  });

program.parseAsync(process.argv).catch((err) => {
  console.error(chalk.red(err instanceof Error ? err.message : String(err)));
  process.exit(1);
});
