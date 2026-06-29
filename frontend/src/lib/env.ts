/**
 * SentinelOps — Typed Environment Variables
 * ==========================================
 * Centralised access to environment configuration with runtime validation.
 * All public env vars must be prefixed with NEXT_PUBLIC_ to be exposed to
 * the browser bundle.
 */

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(
      `[SentinelOps] Missing required environment variable: ${key}. ` +
        `Check your .env.local file.`,
    );
  }
  return value;
}

export const env = {
  /** Backend REST API base URL (no trailing slash). */
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001",

  /** WebSocket URL for live camera feeds. */
  wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8001/ws",

  /** True when running in development mode. */
  isDev: process.env.NODE_ENV === "development",

  /** True when running in production mode. */
  isProd: process.env.NODE_ENV === "production",
} as const;
