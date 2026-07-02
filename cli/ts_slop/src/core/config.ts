/**
 * Server connection configuration.
 *
 * For now this is a single hardcoded constant, per the current stage
 * of the project (no real server yet, no need for env-based
 * environment switching). When a real server exists, this should
 * become resolved from (in priority order):
 *
 *   1. --server flag on the CLI
 *   2. TANDEM_SERVER_URL environment variable
 *   3. a `tandem.config.json` / `.tandemrc` in the project root
 *      (so different projects can point at different deployments)
 *   4. this constant, as the final fallback (e.g. "use the public
 *      Tandem cloud by default")
 *
 * That resolution chain is exactly how most CLIs (kubectl, aws-cli,
 * vercel, etc) handle "where do I send this" -- flag > env > config
 * file > default. Wiring it up now would be premature since there's
 * nothing real to point it at yet; the TODO marks where that logic
 * belongs once the server exists.
 */

export const DEFAULT_SERVER_URL = "https://api.tandem.dev";

export const UPLOAD_ENDPOINT_PATH = "/v1/artifacts/upload";

export interface ServerConfig {
  url: string;
  authToken?: string;
}

/**
 * TODO(server): once the real server exists, replace this with the
 * priority-chain resolution described above. For now, always returns
 * the constant (with an env var override already wired in, since that
 * part costs nothing and is trivially useful even pre-launch -- e.g.
 * for pointing the CLI at a local dev server without code changes).
 */
export function resolveServerConfig(cliFlagUrl?: string): ServerConfig {
  const url = cliFlagUrl ?? process.env.TANDEM_SERVER_URL ?? DEFAULT_SERVER_URL;
  const authToken = process.env.TANDEM_AUTH_TOKEN;
  return { url, authToken };
}
