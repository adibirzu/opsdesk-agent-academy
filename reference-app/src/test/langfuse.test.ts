import { describe, expect, it, vi } from "vitest";
import { ROOT_CONTEXT } from "@opentelemetry/api";
import { TracerProvider, type ReadableSpan } from "@opentelemetry/sdk-trace";
import { createWorkshopTelemetry, metadataOnlySpan } from "@/lib/langfuse.server";
import { analyzeOnServer } from "@/lib/opsdesk-agent.server";
import { presentationText } from "@/lib/langfuse-contract";

// Isolated placeholders only: never read project Secrets or perform live ingestion.
const config = { baseUrl: "https://traces.example.test", publicKey: "isolated-public", secretKey: "isolated-secret" };
describe("Optional Langfuse metadata-only export", () => {
  it("does not export with missing or partial config", async () => {
    const transport = vi.fn();
    for (const cfg of [{}, { baseUrl: config.baseUrl }]) {
      const telemetry = createWorkshopTelemetry(cfg, transport);
      telemetry.authorization(true); telemetry.generationStart(1);
      expect((await telemetry.finish("completed", 1)).status).toBe("not_configured");
    }
    expect(transport).not.toHaveBeenCalled();
  });
  it("rejects unsafe destinations without sending secrets or exposing the URL", async () => {
    const transport = vi.fn();
    for (const baseUrl of ["http://localhost", "https://127.0.0.1", "https://private.internal", "https://traces.example.test/path", "https://user:password@traces.example.test"]) {
      const receipt = await createWorkshopTelemetry({ ...config, baseUrl }, transport).finish("error", 0);
      expect(receipt.status).toBe("invalid_config");
      expect(receipt.traceId).toBeNull();
    }
    expect(transport).not.toHaveBeenCalled();
  });
  it("exports one root, explicit authorization, generation with returned model/usage, and validated tool spans", async () => {
    let captured: Record<string, unknown> = {};
    const transport = vi.fn(async (_url: unknown, init?: RequestInit) => {
      captured = JSON.parse(String(init?.body));
      expect(init?.redirect).toBe("error");
      expect(new Headers(init?.headers).get("x-langfuse-ingestion-version")).toBe("4");
      return new Response("{}", { status: 200 });
    });
    const telemetry = createWorkshopTelemetry(config, transport);
    telemetry.authorization(true); telemetry.generationStart(1);
    telemetry.toolStart("service_health")();
    telemetry.generationEnd("gpt-6-astra", { inputTokens: 12, outputTokens: 8, totalTokens: 20 });
    const receipt = await telemetry.finish("completed", 1);
    expect(receipt.status).toBe("exported"); expect(receipt.readback).toBe("not_verified");
    expect(receipt.traceId).toMatch(/^[a-f0-9]{32}$/); expect(receipt.sessionLabel).toMatch(/^workshop-[a-f0-9]{24}$/);
    expect(receipt.spanCount).toBe(4); expect(transport).toHaveBeenCalledTimes(1);
    const payload = JSON.stringify(captured);
    expect(payload).toContain("generation 1"); expect(payload).toContain("authorization");
    expect(payload).toContain("langfuse.observation.usage_details"); expect(payload).toContain("gpt-6-astra");
    expect(payload).not.toMatch(/traces\.example|isolated-|process\.|host\.|user\.id|input\.value|gen_ai\.prompt|completion|reasoning/);
    const resourceSpans = captured['resourceSpans'] as Array<{ scopeSpans: Array<{ spans: Array<{ traceId: string; parentSpanId?: string; name: string }> }> }>;
    const spans = resourceSpans.flatMap(r => r.scopeSpans.flatMap(s => s.spans));
    expect(new Set(spans.map(s => s.traceId)).size).toBe(1);
    expect(spans.filter(s => !s.parentSpanId)).toHaveLength(1);
    expect((await telemetry.finish("completed", 1)).traceId).toBe(receipt.traceId);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it("awaits the exporter acknowledgment before resolving a run", async () => {
    let release: (response: Response) => void = () => {};
    const transport = vi.fn(() => new Promise<Response>(resolve => { release = resolve; }));
    const telemetry = createWorkshopTelemetry(config, transport);
    let done = false;
    const promise = telemetry.finish("completed", 0).then(r => { done = true; return r; });
    await vi.waitFor(() => expect(transport).toHaveBeenCalledTimes(1));
    expect(done).toBe(false); release(new Response("{}"));
    expect((await promise).status).toBe("exported");
  });
  it("distinguishes partial receipt, HTTP failure and network failure from readback", async () => {
    for (const response of [new Response('{"partialSuccess":{"rejectedSpans":"1"}}'), new Response("private URL or error body", { status: 401 })]) {
      const receipt = await createWorkshopTelemetry(config, async () => response).finish("completed", 0);
      expect(receipt.status).toBe(response.ok ? "partial" : "failed"); expect(receipt.readback).toBe("not_verified");
      expect(Object.keys(receipt)).not.toContain("error");
    }
    const receipt = await createWorkshopTelemetry(config, async () => { throw new Error("private transport detail"); }).finish("completed", 0);
    expect(receipt.status).toBe("failed"); expect(receipt.httpStatus).toBeNull();
  });
  it("drops injected identity, content, endpoint attributes, events, links and resource defaults", () => {
    let ended: ReadableSpan | undefined;
    const provider = new TracerProvider({ spanProcessors: [{ onStart() {}, onEnd(span) { ended = span; }, forceFlush: async () => {}, shutdown: async () => {} }] });
    const span = provider.getTracer("other-instrumentation").startSpan("fixture", {}, ROOT_CONTEXT);
    span.setAttributes({ "user.id": "private identity", "langfuse.observation.input": "private prompt", "http.url": "private endpoint", "langfuse.observation.metadata.validated": true });
    span.addEvent("private answer"); span.end();
    if (!ended) throw new Error("Fixture span did not end");
    const safe = metadataOnlySpan(ended);
    expect(safe.attributes).toEqual({ "langfuse.observation.metadata.validated": true });
    expect(safe.events).toEqual([]); expect(safe.links).toEqual([]);
    expect(safe.resource.attributes).toEqual({ "service.name": "opsdesk-workshop" });
  });
  it("keeps server change blocking and zero model calls when exporting a real blocked execution", async () => {
    const transport = vi.fn(async () => new Response("{}"));
    const telemetry = createWorkshopTelemetry(config, transport); telemetry.authorization(true);
    const apiKey = vi.fn(); const reserve = vi.fn(); const modelFetch = vi.fn();
    const run = await analyzeOnServer({ intent: "change", request: "Change", runbook: "", ticket: { id: "TRAIN-101", title: "Private ticket", description: "private content", service: "payments", priority: "high" } }, { telemetry, apiKey, reserve, accessBlock: async () => null, persistBlock: async () => {}, fetch: modelFetch });
    expect(run.status).toBe("approval_required"); expect(run.modelCalls).toBe(0);
    expect(run.langfuse.status).toBe("exported"); expect(run.langfuse.spanCount).toBe(2);
    expect(apiKey).not.toHaveBeenCalled(); expect(reserve).not.toHaveBeenCalled(); expect(modelFetch).not.toHaveBeenCalled();
    expect(String(transport.mock.calls[0])).not.toContain("private content");
  });
  it("hides private URLs and emails in presentation text", () => {
    expect(presentationText("Contact learner@example.test at https://private.example.test/path")).toBe("Contact [email hidden] at [URL hidden]");
  });
});
describe("Sanitized telemetry failure diagnosis", () => {
  const config = { baseUrl: "https://traces.example.test", publicKey: "isolated-public", secretKey: "isolated-secret" };
  it.each([
    ["timeout", async () => { throw new DOMException("private endpoint and credential details", "TimeoutError"); }],
    ["transport_error", async () => { throw new TypeError("private endpoint and credential details"); }],
    ["http_error", async () => new Response("private upstream error", { status: 403 })],
    ["invalid_response", async () => new Response("private malformed response", { status: 200 })],
  ] as const)("classifies %s without exposing diagnostic values or retrying", async (expected, transport) => {
    const send = vi.fn(transport);
    const telemetry = createWorkshopTelemetry(config, send);
    telemetry.authorization(true);
    const result = await telemetry.finish("approval_required", 0);
    expect(result.status).toBe("failed");
    expect(result.failureCode).toBe(expected);
    expect(result.readback).toBe("not_verified");
    expect(send).toHaveBeenCalledTimes(1);
    expect(JSON.stringify(result)).not.toMatch(/private|traces.example|isolated-/);
  });
});
