export type TelemetryFailureCode = "flush_error" | "serialization_error" | "timeout" | "transport_error" | "http_error" | "invalid_response";
export type LangfuseExport = {
  status: "not_configured" | "invalid_config" | "exported" | "partial" | "failed";
  traceId: string | null;
  sessionLabel: string | null;
  spanCount: number;
  httpStatus: number | null;
  readback: "not_verified";
  failureCode?: TelemetryFailureCode;
};
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
    case "timeout": return "Telemetry request timed out";
    case "transport_error": return "Telemetry transport failed before an HTTP receipt";
    case "http_error": return "Telemetry destination returned an HTTP error";
    case "invalid_response": return "Telemetry response could not be parsed";
    default: return "Failure cause unavailable in this receipt";
  }
}
