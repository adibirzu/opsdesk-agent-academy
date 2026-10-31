import type { TelemetrySetup } from "./telemetry-setup-contract";

export function telemetrySetupPresence(baseUrl: string | undefined, publicKey: string | undefined, secretKey: string | undefined): TelemetrySetup {
  let validHttpsOrigin = false;
  if (baseUrl) {
    try {
      const base = new URL(baseUrl);
      validHttpsOrigin = base.protocol === "https:" && !base.username && !base.password && !base.search && !base.hash && base.pathname === "/" &&
        base.hostname !== "localhost" && !base.hostname.endsWith(".local") && !base.hostname.endsWith(".internal") &&
        !base.hostname.includes(":") && !/^\d+(?:\.\d+){3}$/.test(base.hostname);
    } catch { /* Invalid origins are represented only by a boolean. */ }
  }
  const complete = Boolean(baseUrl) && Boolean(publicKey) && Boolean(secretKey);
  return {
    LANGFUSE_BASE_URL: Boolean(baseUrl),
    LANGFUSE_PUBLIC_KEY: Boolean(publicKey),
    LANGFUSE_SECRET_KEY: Boolean(secretKey),
    validHttpsOrigin,
    status: !complete ? "not_configured" : validHttpsOrigin ? "configured" : "invalid_config",
  };
}