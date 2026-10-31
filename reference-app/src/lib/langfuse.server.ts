import { ROOT_CONTEXT, trace, SpanStatusCode, type Span, type Attributes } from "@opentelemetry/api";
import { TracerProvider, type ReadableSpan, type SpanProcessor } from "@opentelemetry/sdk-trace";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { JsonTraceSerializer } from "@opentelemetry/otlp-transformer";
import { unconfiguredLangfuse, type LangfuseExport } from "./langfuse-contract";

type Config = { baseUrl?: string | undefined; publicKey?: string | undefined; secretKey?: string | undefined };
type Usage = { inputTokens?: number | undefined; outputTokens?: number | undefined; totalTokens?: number | undefined };
export interface WorkshopTelemetry {
  authorization(allowed: boolean): void;
  generationStart(call: number): void;
  generationEnd(model: string | undefined, usage: Usage, call?: number): void;
  toolStart(name: "service_health" | "release_diff"): () => void;
  finish(status: string, calls: number): Promise<LangfuseExport>;
}

const ALLOWED = new Set([
  "langfuse.trace.name", "langfuse.session.id", "langfuse.trace.public", "langfuse.observation.type",
  "langfuse.observation.model.name", "gen_ai.response.model", "langfuse.observation.usage_details",
  "langfuse.observation.metadata.status", "langfuse.observation.metadata.model_calls",
  "langfuse.observation.metadata.authorized", "langfuse.observation.metadata.synthetic",
  "langfuse.observation.metadata.validated", "langfuse.observation.metadata.usage_reported",
]);
// Defense in depth: project only allowed attributes, drop events/links and all resource defaults.
export function metadataOnlySpan(span: ReadableSpan): ReadableSpan {
  const attributes: Attributes = {};
  for (const [key, value] of Object.entries(span.attributes)) if (ALLOWED.has(key)) attributes[key] = value;
  const name = /^(?:OpsDesk workshop run|authorization|generation [1-3]|service_health|release_diff)$/.test(span.name) ? span.name : "workshop span";
  return { name, kind: span.kind, spanContext: () => span.spanContext(), ...(span.parentSpanContext ? { parentSpanContext: span.parentSpanContext } : {}),
    startTime: span.startTime, endTime: span.endTime, status: { code: span.status.code }, attributes, links: [], events: [],
    duration: span.duration, ended: span.ended, resource: resourceFromAttributes({ "service.name": "opsdesk-workshop" }),
    instrumentationScope: { name: "opsdesk.metadata-only", version: "1" }, droppedAttributesCount: 0, droppedEventsCount: 0, droppedLinksCount: 0 };
}
function safeModel(model: string | undefined) {
  return model && /^(?:openai\/)?gpt-[a-z0-9.-]{1,80}$/.test(model) ? model : undefined;
}
function noTelemetry(status: "not_configured" | "invalid_config"): WorkshopTelemetry {
  return { authorization() {}, generationStart() {}, generationEnd() {}, toolStart: () => () => {}, finish: async () => ({ ...unconfiguredLangfuse(), status }) };
}
export function createWorkshopTelemetry(config: Config, transport: typeof fetch = fetch): WorkshopTelemetry {
  if (!config.baseUrl || !config.publicKey || !config.secretKey) return noTelemetry("not_configured");
  let endpoint: URL;
  try {
    const base = new URL(config.baseUrl);
    // No local targets, embedded credentials, paths, query strings or fragments.
    if (base.protocol !== "https:" || base.username || base.password || base.search || base.hash || base.pathname !== "/" ||
      base.hostname === "localhost" || base.hostname.endsWith(".local") || base.hostname.endsWith(".internal") ||
      base.hostname.includes(":") || /^\d+(?:\.\d+){3}$/.test(base.hostname)) return noTelemetry("invalid_config");
    endpoint = new URL("/api/public/otel/v1/traces", base);
  } catch { return noTelemetry("invalid_config"); }
  const spans: ReadableSpan[] = [];
  const processor: SpanProcessor = {
    onStart() {}, onEnd: span => { if (spans.length < 12) spans.push(metadataOnlySpan(span)); },
    forceFlush: async () => {}, shutdown: async () => {},
  };
  // Isolated provider: never register globally or attach HTTP/AI/auth auto-instrumentation.
  const randomHex = (bytes: number) => Array.from(crypto.getRandomValues(new Uint8Array(bytes)), n => n.toString(16).padStart(2, "0")).join("");
  const provider = new TracerProvider({ resource: resourceFromAttributes({ "service.name": "opsdesk-workshop" }),
    idGenerator: { generateTraceId: () => randomHex(16), generateSpanId: () => randomHex(8) },
    spanProcessors: [processor], spanLimits: { attributeCountLimit: 24, attributeValueLengthLimit: 400, eventCountLimit: 0, linkCountLimit: 0 } });
  const tracer = provider.getTracer("opsdesk.metadata-only", "1");
  const sessionLabel = `workshop-${randomHex(12)}`;
  const shared = { "langfuse.trace.name": "OpsDesk workshop run", "langfuse.session.id": sessionLabel, "langfuse.trace.public": false };
  const root = tracer.startSpan("OpsDesk workshop run", { attributes: { ...shared, "langfuse.observation.type": "agent" } }, ROOT_CONTEXT);
  const rootContext = trace.setSpan(ROOT_CONTEXT, root);
  const child = (name: string, type: string) => tracer.startSpan(name, { attributes: { ...shared, "langfuse.observation.type": type } }, rootContext);
  const generations = new Map<number, Span>();
  let authorizationRecorded = false;
  let lastCall = 0;
  let finished: Promise<LangfuseExport> | undefined;
  return {
    authorization(allowed) {
      if (authorizationRecorded) return;
      authorizationRecorded = true;
      const span = child("authorization", "guardrail");
      span.setAttribute("langfuse.observation.metadata.authorized", allowed);
      span.setStatus({ code: allowed ? SpanStatusCode.OK : SpanStatusCode.ERROR });
      span.end();
    },
    generationStart(call) { lastCall = call; generations.set(call, child(`generation ${call}`, "generation")); },
    generationEnd(model, usage, call = lastCall) {
      const span = generations.get(call); if (!span) return;
      const returnedModel = safeModel(model);
      if (returnedModel) { span.setAttribute("langfuse.observation.model.name", returnedModel); span.setAttribute("gen_ai.response.model", returnedModel); }
      const counts: Record<string, number> = {};
      for (const [key, value] of Object.entries({ input: usage.inputTokens, output: usage.outputTokens, total: usage.totalTokens }))
        if (typeof value === "number" && Number.isSafeInteger(value) && value >= 0) counts[key] = value;
      span.setAttribute("langfuse.observation.metadata.usage_reported", Object.keys(counts).length > 0);
      if (Object.keys(counts).length) span.setAttribute("langfuse.observation.usage_details", JSON.stringify(counts));
      span.setStatus({ code: SpanStatusCode.OK }); span.end(); generations.delete(call);
    },
    toolStart(name) {
      const span = child(name, "tool");
      span.setAttributes({ "langfuse.observation.metadata.synthetic": true, "langfuse.observation.metadata.validated": true });
      return () => { span.setStatus({ code: SpanStatusCode.OK }); span.end(); };
    },
    finish(status, calls) {
      finished ??= (async () => {
        for (const span of generations.values()) { span.setStatus({ code: SpanStatusCode.ERROR }); span.end(); }
        generations.clear();
        root.setAttributes({ "langfuse.observation.metadata.status": ["completed", "approval_required", "rate_limited", "error", "unauthorized"].includes(status) ? status : "error", "langfuse.observation.metadata.model_calls": calls });
        root.setStatus({ code: status === "completed" || status === "approval_required" ? SpanStatusCode.OK : SpanStatusCode.ERROR }); root.end();
        const result: LangfuseExport = { status: "failed", traceId: root.spanContext().traceId, sessionLabel, spanCount: spans.length, httpStatus: null, readback: "not_verified" };
        try {
          await provider.forceFlush();
          const body = JsonTraceSerializer.serializeRequest(spans);
          if (!body) return result;
          // Await one bounded telemetry request before returning. Never retry or log credentials/errors.
          const response = await transport(endpoint, { method: "POST", redirect: "error", headers: {
            "Content-Type": "application/json", "Authorization": `Basic ${btoa(`${config.publicKey}:${config.secretKey}`)}`, "x-langfuse-ingestion-version": "4",
          }, body: new TextDecoder().decode(body), signal: AbortSignal.timeout(5000) });
          result.httpStatus = response.status;
          if (!response.ok) { await response.body?.cancel(); return result; }
          const text = await response.text();
          const receipt = text ? JSON.parse(text) as { partialSuccess?: { rejectedSpans?: number | string; errorMessage?: string } } : {};
          result.status = Number(receipt.partialSuccess?.rejectedSpans ?? 0) > 0 || receipt.partialSuccess?.errorMessage ? "partial" : "exported";
          return result;
        } catch { return result; }
        finally { spans.length = 0; await provider.shutdown().catch(() => {}); }
      })();
      return finished;
    },
  };
}