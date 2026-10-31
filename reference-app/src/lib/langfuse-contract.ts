export type TelemetryFailureCode = "flush_error" | "serialization_error" | "request_setup_error" | "timeout" | "transport_error" | "http_error" | "invalid_response";
export type TelemetryFailureHint = "unsupported_timeout" | "request_encoding" | "illegal_invocation" | "redirect" | "dns" | "tls" | "connection_reset" | "network_fetch" | "runtime_policy" | "other";
export type LangfuseExport = {
  status: "not_configured" | "invalid_config" | "exported" | "partial" | "failed";
  traceId: string | null;
  sessionLabel: string | null;
  spanCount: number;
  httpStatus: number | null;
  readback: "not_verified";
  failureCode?: TelemetryFailureCode;
  failureHint?: TelemetryFailureHint;
  redirectTarget?: RedirectTarget;
  redirectPath?: RedirectPath;
  exporterRevision?: "otel-manual-v1";
  failureSignals?: TelemetryFailureSignal[];
};
export type TelemetryFailureSignal = "redirect_mode" | "manual" | "error_mode" | "unsupported" | "follow" | "limit" | "preflight" | "authentication";
const SIGNALS: readonly TelemetryFailureSignal[] = ["redirect_mode", "manual", "error_mode", "unsupported", "follow", "limit", "preflight", "authentication"];
export const safeFailureSignals = (v: unknown): TelemetryFailureSignal[] => Array.isArray(v) ? v.filter((x): x is TelemetryFailureSignal => SIGNALS.includes(x as TelemetryFailureSignal)) : [];
export const exporterRevisionText = (v: unknown) => v === "otel-manual-v1" ? "otel-manual-v1" : "not reported";
export type RedirectTarget = "same_origin" | "langfuse_cloud" | "other_origin" | "unavailable";
export type RedirectPath = "same_path" | "root" | "sign_in" | "other" | "unavailable";
const TARGETS: readonly RedirectTarget[] = ["same_origin", "langfuse_cloud", "other_origin", "unavailable"];
const PATHS: readonly RedirectPath[] = ["same_path", "root", "sign_in", "other", "unavailable"];
export const redirectTargetText = (v: unknown) => TARGETS.includes(v as RedirectTarget) ? v as RedirectTarget : "unavailable";
export const redirectPathText = (v: unknown) => PATHS.includes(v as RedirectPath) ? v as RedirectPath : "unavailable";
export const unconfiguredLangfuse = (): LangfuseExport => ({ status: "not_configured", traceId: null, sessionLabel: null, spanCount: 0, httpStatus: null, readback: "not_verified" });
export function langfuseStatusText(status: LangfuseExport["status"]) {
  switch (status) {
    case "not_configured": return "Langfuse not configured";
    case "invalid_config": return "Langfuse configuration invalid · native AI unaffected";
    case "exported": return "OTLP export acknowledged · trace readback not verified";
    case "partial": return "OTLP partially accepted · trace readback not verified";
    case "failed": return "OTLP export failed · native AI unaffected";
  }
}
// Presentation protection for untrusted displayed text, never used to log secrets.
export function presentationText(text: string) {
  return text.replace(/https?:\/\/[^\s<>"']+/gi, "[URL hidden]").replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[email hidden]");
}
export function langfuseFailureText(code: TelemetryFailureCode | undefined) {
  switch (code) {
    case "flush_error": return "Local span flush failed";
    case "serialization_error": return "Local span serialization failed";
    case "request_setup_error": return "Local telemetry request setup failed";
    case "timeout": return "Telemetry request timed out";
    case "transport_error": return "Telemetry transport failed before an HTTP receipt";
    case "http_error": return "Telemetry destination returned an HTTP error";
    case "invalid_response": return "Telemetry response could not be parsed";
    default: return "Failure cause unavailable in this receipt";
  }
}
export function langfuseFailureHintText(hint: TelemetryFailureHint) {
  switch (hint) {
    case "unsupported_timeout": return "unsupported_timeout";
    case "request_encoding": return "request_encoding";
    case "illegal_invocation": return "illegal_invocation";
    case "redirect": return "redirect";
    case "dns": return "dns";
    case "tls": return "tls";
    case "connection_reset": return "connection_reset";
    case "network_fetch": return "network_fetch";
    case "runtime_policy": return "runtime_policy";
    default: return "other";
  }
}