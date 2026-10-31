import { z } from "zod";
import { unconfiguredLangfuse, type LangfuseExport } from "./langfuse-contract";

export const MAX_MODEL_CALLS = 3;
export const MAX_OUTPUT_TOKENS = 4096;
export const MAX_ANSWER_CHARS = 6000;
export const MAX_TOOL_EVENTS = 4;
export const requestSchema = z.object({
  intent: z.enum(["analyze", "change"]),
  request: z.string().trim().min(1).max(500),
  ticket: z.object({
    id: z.string().regex(/^TRAIN-\d{1,8}$/),
    title: z.string().trim().min(1).max(200),
    description: z.string().trim().min(1).max(4000),
    service: z.string().trim().min(1).max(80),
    priority: z.enum(["high", "medium", "low"]),
  }).strict(),
  runbook: z.string().max(4000),
}).strict();
export type AnalysisInput = z.infer<typeof requestSchema>;
// Keep the model-facing schema small; runtime validation below is stricter.
export const toolSchema = z.object({ service: z.string() }).strict();
export const validatedToolSchema = z.object({ service: z.enum(["payments", "checkout", "catalog"]) }).strict();
export function requiresApproval(input: AnalysisInput) {
  if (input.intent === "change") return true;
  if (/\b(?:change|apply|execute|rollback|restart|redeploy|deploy|delete|remove|disable|enable|modify|update|scale|write|patch|install|kill|reboot)\b|\b(?:roll\s+back|turn\s+(?:off|on)|run\s+(?:a\s+|the\s+)?command)\b/i.test(input.request)) return true;
  // Fail closed on imperative change language, including claims embedded in data.
  const text = [input.request, input.ticket.title, input.ticket.description, input.runbook].join("\n");
  return /\b(?:apply|execute|perform|make|run)\s+(?:the\s+|a\s+|this\s+)?(?:change|rollback|deployment|patch|migration|command)\b|\b(?:roll\s*back|rollback|restart|redeploy|deploy|delete|remove|disable|enable|modify|update|scale|write|patch)\s+(?:the\s+|a\s+|this\s+|all\s+|our\s+)?(?:payments|checkout|catalog|service|production|system|database|config|release|deployment|pods?|files?|records?)\b/i.test(text);
}
export type RunEvent = { type: "model_start" | "model_end" | "tool" | "blocked" | "error"; elapsedMs: number; detail: string; data?: string };
export type AnalysisRun = {
  status: "completed" | "approval_required" | "error" | "rate_limited";
  runId: string | null;
  model: string | null;
  modelCalls: number;
  elapsedMs: number;
  tokenUsage: { input: number | null; output: number | null; total: number | null };
  estimatedCost: null;
  events: RunEvent[];
  answer: string;
  error: string | null;
  upstreamStatus: number | null;
  langfuse: LangfuseExport;
};
export function emptyRun(): AnalysisRun {
  return { status: "error", runId: null, model: null, modelCalls: 0, elapsedMs: 0, tokenUsage: { input: null, output: null, total: null }, estimatedCost: null, events: [], answer: "", error: null, upstreamStatus: null, langfuse: unconfiguredLangfuse() };
}
export function syntheticTool(name: "service_health" | "release_diff", args: unknown, selectedService: string) {
  const { service } = validatedToolSchema.parse(args);
  if (service !== selectedService) throw new Error("Tool service must match the selected ticket.");
  if (name === "service_health") return { synthetic: true, service, observation: service === "payments" ? "Training fixture: p95 latency 1800 ms; error rate 1.2%. Cause unconfirmed." : "Training fixture: healthy; p95 latency 120 ms; error rate 0.1%." };
  return { synthetic: true, service, observation: service === "payments" ? "Training fixture: release r42 changed connection-pool settings. Correlation only; no confirmed root cause." : "Training fixture: no recent release changes." };
}