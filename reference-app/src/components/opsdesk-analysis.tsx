import { useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { LoaderCircle, LogOut, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { lovable } from "@/integrations/lovable/index";
import "@lovable.dev/cloud-auth-js/styles.css";
import { supabase } from "@/integrations/supabase/client";
import { useWorkshopSession } from "./opsdesk-session";
import { analyzeTicket } from "@/lib/opsdesk.functions";
import { requestSchema, type AnalysisInput, type AnalysisRun } from "@/lib/opsdesk-contract";
import { langfuseStatusText, presentationText } from "@/lib/langfuse-contract";
import { checkTelemetrySetup } from "@/lib/telemetry-setup.functions";
import type { TelemetrySetup } from "@/lib/telemetry-setup-contract";

export function OpsdeskAnalysis({ ticket }: { ticket: AnalysisInput["ticket"] }) {
  const { user, ready } = useWorkshopSession();
  const analyze = useServerFn(analyzeTicket);
  const checkSetup = useServerFn(checkTelemetrySetup);
  const [checkingSetup, setCheckingSetup] = useState(false);
  const [setup, setSetup] = useState<TelemetrySetup | null>(null);
  const [setupError, setSetupError] = useState("");
  const setupBusy = useRef(false);
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [error, setError] = useState("");
  const [request, setRequest] = useState("Analyze this synthetic incident using read-only evidence.");
  const [runbook, setRunbook] = useState("");
  async function checkConfiguration() {
    if (setupBusy.current) return;
    setupBusy.current = true;
    setCheckingSetup(true);
    setSetup(null);
    setSetupError("");
    try { setSetup(await checkSetup({ data: {} })); }
    catch { setSetupError("Setup check could not complete. Verify your sign-in and try again."); }
    finally { setupBusy.current = false; setCheckingSetup(false); }
  }
  async function signIn(provider: "lovable" | "google") {
    setError("");
    try {
      const result = await lovable.auth.signInWithOAuth(provider, { redirect_uri: window.location.origin });
      if (result.error) setError(presentationText(result.error.message));
    } catch { setError("Sign-in could not complete. Please try signing in again."); }
  }
  async function execute(intent: "analyze" | "change") {
    if (busy.current) return;
    setError("");
    setRun(null);
    const parsed = requestSchema.safeParse({ ticket, intent, request, runbook });
    if (!parsed.success) { setError(parsed.error.issues.map(i => `${i.path.join(".")}: ${i.message}`).join("; ")); return; }
    busy.current = true;
    setLoading(true);
    try {
      const result = await analyze({ data: parsed.data });
      setRun(result);
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      setError(message.includes("Unauthorized") || message.includes("<!doctype") || message.includes("<html") ? "Your session could not be verified. Sign in again before requesting analysis." : presentationText(message) || "Analysis failed. Please check your sign-in and configuration.");
    }
    finally { busy.current = false; setLoading(false); }
  }
  return <div className="space-y-3 border-t border-border pt-4">
    <h4 className="flex items-center gap-2 font-heading text-lg"><ShieldCheck className="size-4 text-primary" />Lovable AI · read-only</h4>
    {!ready ? <p className="text-sm text-muted-foreground">Checking session…</p> : !user ? <div className="flex flex-wrap gap-2">
      <Button className="lovable-auth-button" onClick={() => void signIn("lovable")}>Continue with Lovable</Button>
      <Button variant="outline" onClick={() => void signIn("google")}>Continue with Google</Button>
    </div> : <>
      <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground"><span>Signed in · workshop session</span><Button variant="ghost" size="icon" title="Sign out" aria-label="Sign out" disabled={loading} onClick={() => void supabase.auth.signOut()}><LogOut /></Button></div>
      <div><label htmlFor="analysis-request" className="text-xs font-medium">Analysis request</label><textarea id="analysis-request" className="field" rows={2} maxLength={500} value={request} disabled={loading} onChange={e => setRequest(e.target.value)} /></div>
      <details><summary className="cursor-pointer text-sm text-muted-foreground">Runbook · untrusted text</summary><label htmlFor="runbook" className="sr-only">Synthetic runbook</label><textarea id="runbook" className="field" rows={3} maxLength={4000} value={runbook} disabled={loading} onChange={e => setRunbook(e.target.value)} /></details>
      <div className="flex flex-wrap gap-2">
        <Button disabled={loading} onClick={() => void execute("analyze")}>{loading && <LoaderCircle className="motion-safe:animate-spin" />}Analyze safely</Button>
        <Button variant="outline" disabled={loading} onClick={() => void execute("change")}>Test a change request</Button>
      </div>
    </>}
    <details className="border-t border-border pt-3">
      <summary className="cursor-pointer text-sm font-medium">Connect Langfuse · optional</summary>
      <div className="mt-2 space-y-2 text-xs text-muted-foreground">
        <p>In this project's Settings → Secrets, save these three server fields:</p>
        <ul className="list-inside list-disc font-mono"><li>LANGFUSE_BASE_URL</li><li>LANGFUSE_PUBLIC_KEY</li><li>LANGFUSE_SECRET_KEY</li></ul>
        <p>Use your instance's HTTPS origin and project keys. Never paste values into the chat or this page. Saving Secrets does not run AI.</p>
        <Button variant="outline" size="sm" disabled={!ready || !user || checkingSetup} onClick={() => void checkConfiguration()}>
          {checkingSetup ? <LoaderCircle className="motion-safe:animate-spin" /> : <ShieldCheck />}Check telemetry setup
        </Button>
        <p>Sign in to check this preview's server configuration. Saving or checking configuration makes zero model calls and sends no traces. Presence does not verify credentials, connectivity or trace delivery.</p>
        {checkingSetup && <p role="status">Checking server configuration…</p>}
        {setupError && <p role="alert">{setupError}</p>}
        {setup && user && <div role="status" aria-live="polite">
          <p className="font-medium">{setup.status === "configured" ? "Langfuse setup present · origin valid" : setup.status === "invalid_config" ? "Langfuse setup present · origin invalid" : "Langfuse not configured"}</p>
          <ul className="list-inside list-disc">
            <li>LANGFUSE_BASE_URL: {setup.LANGFUSE_BASE_URL ? "present" : "missing"}</li>
            <li>LANGFUSE_PUBLIC_KEY: {setup.LANGFUSE_PUBLIC_KEY ? "present" : "missing"}</li>
            <li>LANGFUSE_SECRET_KEY: {setup.LANGFUSE_SECRET_KEY ? "present" : "missing"}</li>
            <li>HTTPS origin: {setup.validHttpsOrigin ? "valid" : "invalid or missing"}</li>
          </ul>
        </div>}
        <p>This integration uses OpenTelemetry HTTP/JSON, not legacy ingestion or the Langfuse JS v6 API. JS v6 requires self-hosted v4.59.0+; older instances need OTLP support (introduced in v3.22.0). Live compatibility is unverified until a real export.</p>
        <p>Only timings, status, random session labels, returned model names, reported token counts and validated synthetic tool names are exported. No identity, ticket text, prompts, answers or reasoning.</p>
        <p>After a signed-in run, copy its Langfuse trace ID from the inspector. Open your Langfuse project → Traces and find that ID or random session label. The instance address stays private. Export acknowledgment is not independent trace readback.</p>
      </div>
    </details>
    <p className="text-xs text-muted-foreground">{run ? langfuseStatusText(run.langfuse.status) : "Langfuse status available after a real run · optional"}</p>
    {loading && <p role="status" aria-live="polite" className="text-sm text-muted-foreground">Analyzing synthetic evidence…</p>}
    {error && <p role="alert" className="break-words text-sm text-primary">{error}</p>}
    {run && <>
      <div role={run.error ? "alert" : "status"} aria-live="polite" className="whitespace-pre-wrap break-words border-l-4 border-primary bg-muted p-3 text-sm">{presentationText(run.error ?? run.answer)}</div>
      <details className="border-t border-border pt-3">
        <summary className="cursor-pointer text-sm font-medium">Run inspector · {run.status} · {run.modelCalls} model calls</summary>
        <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-xs">
          <dt>Status</dt><dd>{run.status}</dd><dt>Gateway run ID</dt><dd className="break-all">{presentationText(run.runId ?? "unknown — no gateway ID reported")}</dd>
          <dt>Model</dt><dd className="break-all">{presentationText(run.model ?? "not called")}</dd><dt>Model calls</dt><dd>{run.modelCalls} / 3</dd>
          <dt>Elapsed</dt><dd>{run.elapsedMs} ms</dd><dt>Tokens in / out / total</dt><dd>{run.tokenUsage.input ?? "unknown"} / {run.tokenUsage.output ?? "unknown"} / {run.tokenUsage.total ?? "unknown"}</dd>
          <dt>Estimated cost</dt><dd>unknown</dd><dt>Tool data</dt><dd>synthetic fixtures only</dd><dt>Langfuse export</dt><dd>{langfuseStatusText(run.langfuse.status)}</dd>
          <dt>Langfuse trace ID</dt><dd className="break-all">{run.langfuse.traceId ?? "none"}</dd>
          <dt>Random session label</dt><dd className="break-all">{run.langfuse.sessionLabel ?? "none"}</dd>
          <dt>Exported span batch</dt><dd>{run.langfuse.spanCount}</dd>
          <dt>Export HTTP status</dt><dd>{run.langfuse.httpStatus ?? "not reported"}</dd>
          <dt>Independent readback</dt><dd>not verified · inspect your Langfuse project</dd>
          {run.upstreamStatus && <><dt>Upstream status</dt><dd>{run.upstreamStatus}</dd></>}
        </dl>
        <ol className="mt-3 space-y-2 border-t border-border pt-3">{run.events.map((e, i) => <li key={i} className="text-xs"><span className="text-muted-foreground">+{e.elapsedMs} ms · {e.type}</span><p className="break-words font-medium">{presentationText(e.detail)}</p>{e.data !== undefined && <pre className="mt-1 whitespace-pre-wrap break-all bg-muted p-2">{presentationText(e.data)}</pre>}</li>)}</ol>
      </details>
    </>}
  </div>;
}