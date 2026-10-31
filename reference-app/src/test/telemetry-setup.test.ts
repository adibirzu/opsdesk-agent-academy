import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const doubles = vi.hoisted(() => ({
  request: vi.fn(), claims: vi.fn(), fetch: vi.fn(), reserve: vi.fn(), mutate: vi.fn(),
  model: vi.fn(), exporter: vi.fn(),
}));
vi.mock("@tanstack/react-start/server", () => ({ getRequest: doubles.request }));
vi.mock("@supabase/supabase-js", () => ({ createClient: () => ({ auth: { getClaims: doubles.claims }, rpc: doubles.reserve, from: doubles.mutate }) }));
// Execute the real auth middleware and readiness handler with an isolated RPC harness.
vi.mock("@tanstack/react-start", () => ({
  createMiddleware: () => ({ server: (server: unknown) => ({ server }) }),
  createServerFn: () => {
    let middleware: Array<{ server: (args: { next: (options: { context: Record<string, unknown> }) => Promise<unknown> }) => Promise<unknown> }> = [];
    let validate: (input: unknown) => unknown = input => input;
    const builder = {
      middleware(items: typeof middleware) { middleware = items; return builder; },
      inputValidator(fn: typeof validate) { validate = fn; return builder; },
      handler(fn: (args: { data: unknown; context: Record<string, unknown> }) => Promise<unknown>) {
        return async ({ data }: { data: unknown }) => {
          const run = async (index: number, context: Record<string, unknown>): Promise<unknown> => {
            const step = middleware[index];
            return step ? step.server({ next: options => run(index + 1, { ...context, ...options.context }) }) : fn({ data: validate(data), context });
          };
          return run(0, {});
        };
      },
    };
    return builder;
  },
}));
vi.mock("@/lib/opsdesk-agent.server", () => { doubles.model(); throw new Error("Readiness must not import the model engine"); });
vi.mock("@/lib/langfuse.server", () => { doubles.exporter(); throw new Error("Readiness must not import the exporter"); });

import { checkTelemetrySetup } from "@/lib/telemetry-setup.functions";
import { telemetrySetupPresence } from "@/lib/telemetry-setup.server";

const fixture = { base: "https://isolated.example.test", public: "isolated-public-fixture", secret: "isolated-secret-fixture" };
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("fetch", doubles.fetch);
  vi.stubEnv("SUPABASE_URL", "https://auth.example.test");
  vi.stubEnv("SUPABASE_PUBLISHABLE_KEY", "isolated-auth-fixture");
  vi.stubEnv("LANGFUSE_BASE_URL", fixture.base);
  vi.stubEnv("LANGFUSE_PUBLIC_KEY", fixture.public);
  vi.stubEnv("LANGFUSE_SECRET_KEY", fixture.secret);
  doubles.request.mockReturnValue(new Request("https://app.example.test", { headers: { authorization: "Bearer fixture.token.only" } }));
  doubles.claims.mockResolvedValue({ data: { claims: { sub: "isolated-user", is_anonymous: false } }, error: null });
});
afterEach(() => {
  expect(doubles.fetch).not.toHaveBeenCalled();
  expect(doubles.model).not.toHaveBeenCalled();
  expect(doubles.exporter).not.toHaveBeenCalled();
  expect(doubles.reserve).not.toHaveBeenCalled();
  expect(doubles.mutate).not.toHaveBeenCalled();
  vi.unstubAllEnvs(); vi.unstubAllGlobals();
});

describe("Authenticated presence-only telemetry setup", () => {
  it("rejects signed-out callers through the existing auth middleware", async () => {
    doubles.request.mockReturnValue(new Request("https://app.example.test"));
    await expect(checkTelemetrySetup({ data: {} })).rejects.toThrow("Unauthorized");
    expect(doubles.claims).not.toHaveBeenCalled();
  });
  it("rejects an invalid authenticated session", async () => {
    doubles.claims.mockResolvedValue({ data: null, error: new Error("isolated auth denial") });
    await expect(checkTelemetrySetup({ data: {} })).rejects.toThrow("Unauthorized");
  });
  it("rejects anonymous authenticated callers", async () => {
    doubles.claims.mockResolvedValue({ data: { claims: { sub: "isolated-user", is_anonymous: true } }, error: null });
    await expect(checkTelemetrySetup({ data: {} })).rejects.toThrow("non-anonymous");
  });
  it("requires a strict empty object", async () => {
    for (const data of [undefined, null, [], { extra: true }]) {
      await expect(checkTelemetrySetup({ data: data as unknown as Record<string, never> })).rejects.toThrow();
    }
  });
  it("returns exactly four booleans and configured status, never fixture values or identities", async () => {
    const result = await checkTelemetrySetup({ data: {} });
    expect(result).toEqual({ LANGFUSE_BASE_URL: true, LANGFUSE_PUBLIC_KEY: true, LANGFUSE_SECRET_KEY: true, validHttpsOrigin: true, status: "configured" });
    const output = JSON.stringify(result);
    for (const value of [...Object.values(fixture), "isolated-user", "fixture.token.only"]) expect(output).not.toContain(value);
  });
  it("reports each missing binding without sending an export", async () => {
    for (const name of ["LANGFUSE_BASE_URL", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"] as const) {
      vi.stubEnv(name, "");
      const result = await checkTelemetrySetup({ data: {} });
      expect(result.status).toBe("not_configured");
      expect(result[name]).toBe(false);
      vi.stubEnv(name, name === "LANGFUSE_BASE_URL" ? fixture.base : name === "LANGFUSE_PUBLIC_KEY" ? fixture.public : fixture.secret);
    }
    expect(telemetrySetupPresence(undefined, undefined, undefined)).toEqual({ LANGFUSE_BASE_URL: false, LANGFUSE_PUBLIC_KEY: false, LANGFUSE_SECRET_KEY: false, validHttpsOrigin: false, status: "not_configured" });
  });
  it("reports invalid origins with only booleans and status", async () => {
    for (const base of ["malformed-origin-fixture", "http://isolated.example.test", "https://localhost", "https://127.0.0.1", "https://private.internal", "https://private.local", "https://[::1]", "https://isolated.example.test/path", "https://isolated.example.test?query", "https://isolated.example.test#fragment", "https://user:password@isolated.example.test"]) {
      vi.stubEnv("LANGFUSE_BASE_URL", base);
      const result = await checkTelemetrySetup({ data: {} });
      expect(result).toEqual({ LANGFUSE_BASE_URL: true, LANGFUSE_PUBLIC_KEY: true, LANGFUSE_SECRET_KEY: true, validHttpsOrigin: false, status: "invalid_config" });
      expect(JSON.stringify(result)).not.toContain(base);
    }
  });
});