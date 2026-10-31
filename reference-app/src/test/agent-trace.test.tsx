import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AgentTrace } from "@/components/agent-trace";
import { emptyRun } from "@/lib/opsdesk-contract";
import { traceEvents } from "@/lib/agent-trace";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("current-run Agent trace (isolated only)", () => {
  it("maps actual events chronologically without copying payload or arbitrary labels", () => {
    expect(traceEvents([
      { type: "model_end", elapsedMs: 30, detail: "private finish reason", data: "private payload" },
      { type: "tool", elapsedMs: 20, detail: "service_health", data: "raw arguments" },
      { type: "model_start", elapsedMs: 10, detail: "private model" },
      { type: "tool", elapsedMs: 25, detail: "release_diff: rejected" },
      { type: "blocked", elapsedMs: 0, detail: "private authorization reason" },
    ]).map(({ elapsedMs, label }) => [elapsedMs, label])).toEqual([
      [0, "Authorization / safety policy blocked execution"],
      [10, "Model call started"],
      [20, "service_health · validated synthetic tool"],
      [25, "release_diff · tool rejected"],
      [30, "Model step finished"],
    ]);
  });

  it("shows the current run counts and reported tokens, not fixture defaults", () => {
    const run = emptyRun();
    run.modelCalls = 2; run.elapsedMs = 127;
    run.tokenUsage = { input: 80, output: 21, total: 101 };
    render(<AgentTrace run={run} />);
    expect(screen.getByText("80 / 21 / 101")).toBeInTheDocument();
    expect(screen.getByText("127 ms")).toBeInTheDocument();
    expect(screen.getByText("Model calls").nextElementSibling?.textContent).toBe("2");
    expect(screen.queryByText("Model call started")).not.toBeInTheDocument();
  });

  it("shows a policy block with zero generations and unknown usage", () => {
    const run = emptyRun(); run.status = "approval_required";
    run.events = [{ type: "blocked", elapsedMs: 1, detail: "Explicit change intent blocked on the server; zero model calls." }];
    render(<AgentTrace run={run} />);
    expect(screen.getByText("Model calls").nextElementSibling?.textContent).toBe("0");
    expect(screen.getByText("unknown / unknown / unknown")).toBeInTheDocument();
    expect(screen.getByText("Authorization / safety policy blocked execution")).toBeInTheDocument();
    expect(screen.queryByText("Model call started")).not.toBeInTheDocument();
  });

  it.each(["not_configured", "failed"] as const)("reports %s without claiming arrival or making requests", status => {
    const network = vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Forbidden"));
    const run = emptyRun(); run.langfuse.status = status;
    render(<AgentTrace run={run} />);
    expect(screen.getByText(status === "failed" ? /Langfuse exporter · OTLP export failed/ : /Langfuse exporter · Langfuse not configured/)).toBeInTheDocument();
    expect(screen.getByText("No successful export acknowledgment. Independent arrival has not been verified.")).toBeInTheDocument();
    expect(network).not.toHaveBeenCalled();
  });

  it("withholds identities, raw data, model text and unsafe identifiers even after disclosure", () => {
    const run = emptyRun();
    run.model = "Private Person"; run.runId = "account-identity"; run.answer = "hidden reasoning";
    run.events = [{ type: "error", elapsedMs: 5, detail: "person@example.test https://private.example.test", data: '{"raw":"payload"}' }];
    run.langfuse.traceId = "https://private.example.test"; run.langfuse.sessionLabel = "person@example.test";
    const { container } = render(<AgentTrace run={run} />);
    fireEvent.click(screen.getByText("Trace identifiers · presentation-safe disclosure"));
    for (const forbidden of ["Private Person", "account-identity", "hidden reasoning", "person@example.test", "https://private.example.test", "payload"]) expect(container.textContent).not.toContain(forbidden);
    expect(screen.getByRole("button", { name: "Copy trace ID" })).toBeDisabled();
  });

  it("discloses only valid current identifiers and reports clipboard success and failure", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const run = emptyRun();
    run.langfuse = { status: "exported", traceId: "a".repeat(32), sessionLabel: `workshop-${"b".repeat(24)}`, spanCount: 4, httpStatus: 200, readback: "not_verified" };
    const { container } = render(<AgentTrace run={run} />);
    expect(container.querySelector("details")?.open).toBe(false);
    expect(screen.getByText("Actual exported span batch: 4 · HTTP status: 200")).toBeInTheDocument();
    expect(screen.getByText("Export acknowledged; independently open Langfuse to verify arrival.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Trace identifiers · presentation-safe disclosure"));
    fireEvent.click(screen.getByRole("button", { name: "Copy trace ID" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Trace ID copied."));
    expect(writeText).toHaveBeenLastCalledWith("a".repeat(32));
    writeText.mockRejectedValueOnce(new Error("private clipboard error"));
    fireEvent.click(screen.getByRole("button", { name: "Copy session label" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Session label could not be copied."));
    expect(screen.getByRole("status")).not.toHaveTextContent("private clipboard error");
  });
});