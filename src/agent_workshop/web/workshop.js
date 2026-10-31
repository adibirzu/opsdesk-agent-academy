(() => {
  "use strict";
  const form = document.getElementById("run-form");
  const prompt = document.getElementById("prompt");
  const session = document.getElementById("session-id");
  const role = document.getElementById("agent-role");
  const token = document.getElementById("token");
  const forget = document.getElementById("forget-token");
  const count = document.getElementById("prompt-count");
  const message = document.getElementById("form-message");
  const announcement = document.getElementById("announcement");
  const empty = document.getElementById("empty-state");
  const result = document.getElementById("result-state");
  const status = document.getElementById("run-status");
  let tabToken = "";
  let busy = false;
  const controls = [...form.querySelectorAll("button, input, textarea, select")];
  let accessChecked = false;
  function accessState() { text("access-state", accessChecked ? "Access code accepted. You can run another investigation in this tab." : tabToken ? "Access code added. Select Run investigation to check it and start the agent." : "Waiting for your access code. It stays in this tab and is cleared when you reload."); }

  function announce(text) { announcement.textContent = text; }
  function updateCount() { count.textContent = `${prompt.value.length.toLocaleString()} / 16,000`; }
  function showMessage(text) { message.textContent = text; message.hidden = !text; }
  function setStatus(label, kind) { status.textContent = label; status.className = `state-pill state-${kind}`; }
  function setBusy(value) { busy = value; controls.forEach((control) => { control.disabled = value; }); }
  function text(id, value) { document.getElementById(id).textContent = value == null || value === "" ? "—" : String(value); }
  function steps(items) {
    const list = document.getElementById("model-steps");
    list.replaceChildren();
    if (typeof items === "number") { const li = document.createElement("li"); li.textContent = `${items} bounded model step${items === 1 ? "" : "s"} recorded.`; list.append(li); return; }
    if (!Array.isArray(items) || !items.length) { const li = document.createElement("li"); li.textContent = "No model steps recorded."; list.append(li); return; }
    items.forEach((item) => { const li = document.createElement("li"); li.textContent = typeof item === "string" ? item : JSON.stringify(item); list.append(li); });
  }
  function render(data, httpStatus) {
    empty.hidden = true; result.hidden = false;
    const outcome = data && data.outcome ? data.outcome : "failure";
    const policy = outcome === "approval_required" || httpStatus === 409;
    const failed = outcome === "failure" || httpStatus >= 400;
    const banner = document.getElementById("result-banner");
    banner.className = `result-banner${policy ? " is-policy" : failed ? " is-error" : ""}`;
    document.getElementById("result-symbol").textContent = policy ? "△" : failed ? "×" : "●";
    text("result-title", policy ? "Approval required" : failed ? "Run did not complete" : "Run completed");
    text("result-summary", policy ? "The security policy blocked this action before the model ran. Nothing was changed. Try Run investigation to continue." : failed ? ((data && data.error) || "The bounded run reported a failure.") : data && data.inference_mode === "scripted_rehearsal" ? "Scripted rehearsal completed; no model provider was contacted." : "The agent finished. Read its answer below, then use the trace ID to check its activity in your monitoring tools.");
    text("answer", policy ? "The policy stopped this request before the model ran. No remediation was executed." : data && data.answer); text("outcome", outcome); text("decision", data && data.decision);
    text("inference-mode", policy ? "not invoked" : data && data.inference_mode === "scripted_rehearsal" ? "scripted rehearsal" : data && data.model ? `${data.model} · ${data.inference_mode || "mode unreported"}` : "unavailable");
    text("tool-data", data && data.tool_data === "synthetic" ? "synthetic · workshop fixtures" : "not established");
    text("agent-role-result", data && data.agent_role);
    const estimate = data && data.estimated_cost_usd;
    text("estimated-cost", typeof estimate === "number" && Number.isFinite(estimate) && estimate >= 0 ? `$${estimate.toFixed(8)}` : "Unknown · usage or rates unavailable");
    text("trace-session", data && data.session_id); text("trace-run", data && data.run_id); text("trace-id", data && data.trace_id);
    steps(data && data.steps);
    const telemetry = data && (data.telemetry || data.delivery || {});
    const exportersDisabled = Array.isArray(telemetry.exporters) && telemetry.exporters.length === 0;
    document.querySelector(".pending-tag").textContent = exportersDisabled ? "Not enabled" : "Check in monitoring tools";
    text("telemetry-help", exportersDisabled ? "This run has no trace exporters configured. In the offline rehearsal, no model or cloud monitoring service is contacted." : "These statuses describe sending data. This page does not check whether it is searchable yet. Use the trace ID in your configured APM, Langfuse or Log Analytics installation to verify this run.");
    text("exporter-state", exportersDisabled ? "Not enabled for this run" : telemetry.flush_ok === true ? "Sent · visibility not checked" : telemetry.flush_ok === false ? "Sending incomplete · check configuration" : "Not reported");
    text("log-state", data && data.log_upload ? `${data.log_upload.status} · visibility not checked` : "Not reported");
    text("metric-state", data && data.metrics_upload ? `${data.metrics_upload.status} · visibility not checked` : "Not reported");
    const kind = policy ? "policy" : failed ? "error" : "success"; setStatus(policy ? "Policy stop" : failed ? "Failure" : "Complete", kind);
    announce(policy ? "Approval required. No remediation was executed." : failed ? "Run failed." : "Run completed. Results are ready.");
  }
  async function run(operation, failTool) {
    if (busy) return;
    showMessage("");
    if (!form.reportValidity()) { announce("Correct the required fields before running."); return; }
    if (!tabToken) { showMessage("Add your workshop access code at the top of this form, then select Run investigation. Ask your presenter if you do not have a code."); token.setAttribute("aria-invalid", "true"); token.focus(); announce("Workshop access code needed. No request has been sent."); return; }
    setBusy(true); setStatus("Running", "running");
    result.hidden = true; empty.hidden = false;
    text("waiting-title", operation === "remediate" ? "Checking the action against the security policy…" : "The agent is investigating…");
    text("waiting-description", "Waiting for the service to respond. This can take a little time. Results will appear here; you do not need to click again.");
    announce("Request sent. Waiting for results.");
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 120000);
    try {
      const response = await fetch("/run", { method: "POST", credentials: "omit", redirect: "error", cache: "no-store", signal: controller.signal, headers: { "Content-Type": "application/json", "X-Workshop-Token": tabToken }, body: JSON.stringify({ prompt: prompt.value, session_id: session.value, operation, fail_tool: Boolean(failTool), agent_role: role.value }) });
      let data = null; try { data = await response.json(); } catch (_) { data = { outcome: "failure", error: "The service returned an unreadable response." }; }
      if (response.status === 401) { tabToken = ""; accessChecked = false; token.value = ""; forget.hidden = true; token.setAttribute("aria-invalid", "true"); showMessage("That access code was not accepted. Check it with your presenter, paste it above and try again."); data = { outcome: "failure", error: "The access code was not accepted. The agent did not run." }; }
      if (response.status === 400) data = { outcome: "failure", error: "The request was rejected as invalid. Check the session label and prompt." };
      if ((response.status === 502 || response.status === 503) && !(data && data.trace_id)) data = { outcome: "failure", error: "The workshop service could not complete this bounded run." };
      render(data, response.status);
      if (response.ok || response.status === 409 || (data && data.trace_id)) { accessChecked = true; token.value = ""; token.removeAttribute("aria-invalid"); token.placeholder = "Access code kept for this tab"; forget.hidden = false; }
    } catch (error) {
      const timedOut = error && error.name === "AbortError"; render({ outcome: "failure", error: timedOut ? "The 120-second request window elapsed. No retry was attempted." : "Network request failed. Check the same-origin workshop service." }, 0);
    } finally { clearTimeout(timer); setBusy(false); accessState(); if (!tabToken) { token.placeholder = "Paste your workshop access code"; token.focus(); } }
  }
  prompt.addEventListener("input", updateCount); updateCount();
  token.addEventListener("input", () => { tabToken = token.value; accessChecked = false; forget.hidden = !tabToken; token.removeAttribute("aria-invalid"); showMessage(""); accessState(); });
  forget.addEventListener("click", () => { tabToken = ""; accessChecked = false; token.value = ""; token.placeholder = "Paste your workshop access code"; forget.hidden = true; token.removeAttribute("aria-invalid"); showMessage("Access code cleared. Add it again before running another investigation."); accessState(); token.focus(); announce("Workshop access code cleared."); });
  form.addEventListener("submit", (event) => { event.preventDefault(); run("investigate", false); });
  document.querySelector("[data-testid='remediate']").addEventListener("click", () => run("remediate", false));
  document.querySelector("[data-testid='fail-tool']").addEventListener("click", () => run("investigate", true));
})();
