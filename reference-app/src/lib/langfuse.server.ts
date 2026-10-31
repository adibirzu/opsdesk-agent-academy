import { ROOT_CONTEXT, trace, SpanStatusCode, type Span, type Attributes } from "@opentelemetry/api";
import { TracerProvider, type ReadableSpan, type SpanProcessor } from "@opentelemetry/sdk-trace";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { JsonTraceSerializer } from "@opentelemetry/otlp-transformer";
import { unconfiguredLangfuse, type LangfuseExport, type TelemetryFailureSignal, type RedirectTarget, type RedirectPath } from "./langfuse-contract";

// Server-only Location classification; the raw Location value is never returned or logged.
export function classifyRedirect(location: string | null, endpoint: URL): { redirectTarget: RedirectTarget; redirectPath: RedirectPath } {
  if (!location) return { redirectTarget: "unavailable", redirectPath: "unavailable" };
  let target: URL;
  try { target = new URL(location, endpoint); } catch { return { redirectTarget: "unavailable", redirectPath: "unavailable" }; }
  const redirectTarget: RedirectTarget = target.origin === endpoint.origin ? "same_origin"
    : target.protocol === "https:" && !target.port && (target.hostname === "cloud.langfuse.com" || target.hostname === "us.cloud.langfuse.com") ? "langfuse_cloud" : "other_origin";
  const path = target.pathname.toLowerCase();
  const redirectPath: RedirectPath = path === endpoint.pathname.toLowerCase() ? "same_path" : path === "/" ? "root"
    : /(?:^|\/)(?:sign-?in|login|auth)(?:\/|$)/.test(path) ? "sign_in" : "other";
  return { redirectTarget, redirectPath };
}

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
// Inspect exception text only to select a fixed category; never return or log it.
export function telemetryFailureHint(error: unknown): NonNullable<LangfuseExport["failureHint"]> {
  const message = typeof error === "object" && error !== null && "message" in error && typeof error.message === "string" ? error.message.toLowerCase() : "";
  if (/abortsignal.*timeout|timeout is not a function/.test(message)) return "unsupported_timeout";
  if (/btoa|latin1|invalid character|header/.test(message)) return "request_encoding";
  if (/illegal invocation|invalid receiver/.test(message)) return "illegal_invocation";
  if (/redirect/.test(message)) return "redirect";
  if (/enotfound|eai_again|dns/.test(message)) return "dns";
  if (/certificate|tls|ssl/.test(message)) return "tls";
  if (/econnreset|econnrefused|connection reset|socket/.test(message)) return "connection_reset";
  if (/not allowed|disallowed|blocked|cross.origin|cors/.test(message)) return "runtime_policy";
  if (/failed to fetch|fetch failed|network/.test(message)) return "network_fetch";
  return "other";
}
// Fixed diagnostic keywords only; the exception text itself is never returned or logged.
export function telemetryFailureSignals(error: unknown): TelemetryFailureSignal[] {
  const message = typeof error === "object" && error !== null && "message" in error && typeof error.message === "string" ? error.message.toLowerCase() : "";
  const patterns: Array<[TelemetryFailureSignal, RegExp]> = [
    ["redirect_mode", /redirect.*mode|mode.*redirect/], ["manual", /\bmanual\b/],
    ["error_mode", /mode.*['"]?error|redirect.*['"]error['"]/], ["unsupported", /unsupported|not supported|not implemented/],
    ["follow", /\bfollow\b/], ["limit", /too many|limit|exceeded/], ["preflight", /preflight/], ["authentication", /unauthorized|authentication|sign.?in/],
  ];
  return patterns.filter(([, pattern]) => pattern.test(message)).map(([name]) => name);
}
export function createWorkshopTelemetry(config: Config, transport: typeof fetch = (input, init) => globalThis.fetch(input, init)): WorkshopTelemetry {
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
        const result: LangfuseExport = { status: "failed", traceId: root.spanContext().traceId, sessionLabel, spanCount: spans.length, httpStatus: null, readback: "not_verified", exporterRevision: "otel-manual-v1" };
        let stage: "flush_error" | "serialization_error" | "request_setup_error" | "transport_error" | "invalid_response" = "flush_error";
        try {
          await provider.forceFlush();
          stage = "serialization_error";
          const body = JsonTraceSerializer.serializeRequest(spans);
          if (!body) { result.failureCode = "serialization_error"; return result; }
          // Await one bounded telemetry request before returning. Never retry or log credentials/errors.
          const serializedBody = new TextDecoder().decode(body);
          stage = "request_setup_error";
          const headers = {
            "Content-Type": "application/json", "Authorization": `Basic ${btoa(`${config.publicKey}:${config.secretKey}`)}`, "x-langfuse-ingestion-version": "4",
          };
          const signal = AbortSignal.timeout(5000);
          stage = "transport_error";
          const response = await transport(endpoint.href, { method: "POST", redirect: "manual", headers, body: serializedBody, signal });
          // Manual mode never follows. An opaque redirect (status 0) or any 3xx is reported, not retried.
          if (response.type === "opaqueredirect" || (response.status >= 300 && response.status < 400)) {
            result.httpStatus = response.status >= 300 ? response.status : null;
            result.failureCode = "http_error"; result.failureHint = "redirect";
            Object.assign(result, response.type === "opaqueredirect" ? { redirectTarget: "unavailable", redirectPath: "unavailable" } : classifyRedirect(response.headers.get("location"), endpoint));
            await response.body?.cancel().catch(() => {}); return result;
          }
          result.httpStatus = response.status;
          if (!response.ok) { result.failureCode = "http_error"; await response.body?.cancel(); return result; }
          stage = "invalid_response";
          const text = await response.text();
          const receipt = text ? JSON.parse(text) as { partialSuccess?: { rejectedSpans?: number | string; errorMessage?: string } } : {};
          result.status = Number(receipt.partialSuccess?.rejectedSpans ?? 0) > 0 || receipt.partialSuccess?.errorMessage ? "partial" : "exported";
          return result;
        } catch (error) {
          // Bounded name check (works for cross-realm DOMException); the error itself is never returned or logged.
          const name = typeof error === "object" && error !== null && "name" in error ? (error as { name: unknown }).name : undefined;
          result.failureCode ??= stage === "transport_error" && (name === "TimeoutError" || name === "AbortError") ? "timeout" : stage;
          result.failureHint = telemetryFailureHint(error);
          result.failureSignals = telemetryFailureSignals(error);
          return result;
        }
        finally { spans.length = 0; await provider.shutdown().catch(() => {}); }
      })();
      return finished;
    },
  };
}