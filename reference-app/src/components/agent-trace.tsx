import { useState } from "react";
import { Copy, ListTree } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AnalysisRun } from "@/lib/opsdesk-contract";
import { langfuseStatusText, langfuseFailureText } from "@/lib/langfuse-contract";
import { safeCount, traceEvents, traceIdentifiers } from "@/lib/agent-trace";

export function AgentTrace({ run }: { run: AnalysisRun }) {
  const events = traceEvents(run.events);
  const ids = traceIdentifiers(run.langfuse.traceId, run.langfuse.sessionLabel);
  const [feedback, setFeedback] = useState("");
  const count = (value: number | null) => safeCount(value) ?? "unknown";
  async function copy(value: string | null, label: string) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setFeedback(`${label} copied.`);
    } catch { setFeedback(`${label} could not be copied. Select the identifier and copy it manually.`); }
  }
  return <section aria-label="Agent trace" className="space-y-3 border-t border-border pt-3">
    <h4 className="flex items-center gap-2 font-heading text-lg"><ListTree className="size-4 text-primary" />Agent trace</h4>
    <p className="text-xs font-medium">Recorded by this app</p>
    <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs">
      <dt>Model calls</dt><dd>{count(run.modelCalls)}</dd>
      <dt>Reported tokens · input / output / total</dt><dd>{count(run.tokenUsage.input)} / {count(run.tokenUsage.output)} / {count(run.tokenUsage.total)}</dd>
      <dt>Elapsed</dt><dd>{count(run.elapsedMs)} ms</dd>
    </dl>
    {events.length ? <ol aria-label="Recorded events" className="space-y-2 border-l border-border pl-3">
      {events.map(event => <li key={event.index} className="text-xs"><span className="text-muted-foreground">+{event.elapsedMs ?? "unknown"} ms</span><p className="break-words font-medium">{event.label}</p></li>)}
    </ol> : <p className="text-xs text-muted-foreground">No execution events recorded for this run.</p>}
    <p className="text-xs text-muted-foreground">Successful sign-in authorization is not recorded in run.events; no authorization event is inferred.</p>
    <div className="space-y-1 border-t border-border pt-2 text-xs">
      <p className="font-medium">Langfuse exporter · {langfuseStatusText(run.langfuse.status)}</p>
      {run.langfuse.status === "failed" && <p>Failure diagnosis: {langfuseFailureText(run.langfuse.failureCode)}. No automatic retry was made.</p>}
      <p>Actual exported span batch: {count(run.langfuse.spanCount)} · HTTP status: {count(run.langfuse.httpStatus)}</p>
      {(run.langfuse.status === "exported" || run.langfuse.status === "partial")
        ? <p>Export acknowledged{run.langfuse.status === "partial" ? " partially" : ""}; independently open Langfuse to verify arrival.</p>
        : <p>No successful export acknowledgment. Independent arrival has not been verified.</p>}
    </div>
    <details onToggle={() => setFeedback("")}>
      <summary className="cursor-pointer text-xs font-medium">Trace identifiers · presentation-safe disclosure</summary>
      <div className="mt-2 space-y-2 text-xs">
        <dl className="space-y-1"><dt>Trace ID</dt><dd className="break-all font-mono">{ids.traceId ?? "unavailable"}</dd><dt>Random session label</dt><dd className="break-all font-mono">{ids.sessionLabel ?? "unavailable"}</dd></dl>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={!ids.traceId} onClick={() => void copy(ids.traceId, "Trace ID")}><Copy />Copy trace ID</Button>
          <Button variant="outline" size="sm" disabled={!ids.sessionLabel} onClick={() => void copy(ids.sessionLabel, "Session label")}><Copy />Copy session label</Button>
        </div>
        <p>Open your own Langfuse project → Tracing, locate this exact trace/session, then expand the agent root.</p>
        <p role="status" aria-live="polite">{feedback}</p>
      </div>
    </details>
  </section>;
}