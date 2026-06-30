import chalk from "chalk";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolveServerConfig } from "../core/config.js";
import { uploadArtifact } from "../core/upload.js";

export interface UploadCommandOptions {
  artifactPath: string;
  projectName: string;
  projectVersion: string;
  serverUrl?: string;
}

export async function runUpload(opts: UploadCommandOptions): Promise<boolean> {
  const server = resolveServerConfig(opts.serverUrl);

  console.log(chalk.bold(`Uploading to ${server.url}...`));

  const bytes = await readFile(opts.artifactPath);
  const clientHash = createHash("sha256").update(bytes).digest("hex");

  const result = await uploadArtifact(opts.artifactPath, server, {
    projectName: opts.projectName,
    projectVersion: opts.projectVersion,
    clientHash,
  });

  if (result.ok) {
    console.log(`  ${chalk.green("✓")} Upload succeeded (HTTP ${result.status})`);
    if (result.body) {
      console.log(chalk.dim(`      ${JSON.stringify(result.body)}`));
    }
    return true;
  }

  if (result.status === 0) {
    console.log(
      `  ${chalk.red("✗")} Could not reach server at ${server.url}: ${result.error}`,
    );
    console.log(
      chalk.dim(
        "      No real Tandem server exists yet -- this is expected until the server is implemented.",
      ),
    );
  } else {
    console.log(`  ${chalk.red("✗")} Upload failed (HTTP ${result.status})`);
    if (result.body) console.log(chalk.dim(`      ${JSON.stringify(result.body)}`));
  }
  return false;
}
