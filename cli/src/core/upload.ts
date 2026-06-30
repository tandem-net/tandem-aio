import { readFile } from "node:fs/promises";
import path from "node:path";
import type { ServerConfig } from "./config.js";
import { UPLOAD_ENDPOINT_PATH } from "./config.js";

/**
 * Uploads a built .tandem artifact to the server.
 *
 * TRANSFER MECHANISM: multipart/form-data POST, one field carrying the
 * artifact as a binary file part.
 *
 * Why this over the alternatives:
 *
 *   - Raw JSON body with base64-encoded artifact bytes: works, but
 *     inflates binary payloads by ~33% and forces the whole artifact
 *     into memory as a string on both ends. Fine for tiny payloads,
 *     wasteful once artifacts carry real WASM + bundled immutable data
 *     (model weights, lookup tables) that can run into MBs.
 *
 *   - Raw binary POST (Content-Type: application/octet-stream, no
 *     multipart envelope): slightly simpler, but loses the ability to
 *     send metadata (project name, CLI version, client-computed hash
 *     for integrity check) alongside the bytes in the same request
 *     without inventing custom headers for everything. Multipart gives
 *     you a clean place for both without custom header sprawl.
 *
 *   - gRPC / protobuf streaming: the "real" answer for a production
 *     system at scale (supports streaming large payloads, backpressure,
 *     bidirectional progress reporting), but it's a bigger commitment
 *     (server has to speak gRPC, schema versioning, etc) that doesn't
 *     make sense before the server itself exists. Worth revisiting once
 *     the server's transport layer is decided.
 *
 *   - Presigned-URL upload (CLI asks server for a short-lived S3-style
 *     upload URL, then PUTs directly to object storage, bypassing the
 *     application server entirely): this is what you'd want once
 *     artifacts get large and/or upload volume is high, since it keeps
 *     big binary transfer off your API server entirely. Documented here
 *     as the natural next step, not implemented now since there's no
 *     object storage backing it yet.
 *
 * multipart/form-data is the right choice for THIS stage: simple,
 * universally supported by every HTTP server framework, handles binary
 * + metadata cleanly, and is a one-line swap to a presigned-URL flow
 * later (the CLI-side interface below doesn't need to change shape,
 * just what's inside `uploadArtifact`).
 */

export interface UploadResult {
  ok: boolean;
  status: number;
  body?: unknown;
  error?: string;
}

export async function uploadArtifact(
  artifactPath: string,
  server: ServerConfig,
  meta: { projectName: string; projectVersion: string; clientHash: string },
): Promise<UploadResult> {
  const bytes = await readFile(artifactPath);
  const filename = path.basename(artifactPath);

  const form = new FormData();
  form.append(
    "artifact",
    new Blob([bytes], { type: "application/zip" }),
    filename,
  );
  form.append("project_name", meta.projectName);
  form.append("project_version", meta.projectVersion);
  form.append("client_hash", meta.clientHash);
  form.append("cli_version", "0.1.0");

  const url = new URL(UPLOAD_ENDPOINT_PATH, server.url).toString();

  const headers: Record<string, string> = {};
  if (server.authToken) {
    headers.Authorization = `Bearer ${server.authToken}`;
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers,
      body: form,
    });

    let body: unknown;
    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      body = await res.json().catch(() => undefined);
    }

    return { ok: res.ok, status: res.status, body };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
