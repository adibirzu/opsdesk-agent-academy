import type { RunEvent } from "./opsdesk-contract";

// Never render event detail/data: only recognize fixed, server-emitted markers.
export function traceEvents(events: RunEvent[]) {
  return events.map((event, index) => {
    let label: string;
    switch (event.type) {
      case "model_start": label = "Model call started"; break;
      case "model_end": label = "Model step finished"; break;
      case "tool":
        label = event.detail === "service_health" || event.detail === "release_diff"
          ? `${event.detail} · validated synthetic tool`
          : event.detail === "service_health: rejected" || event.detail === "release_diff: rejected"
            ? `${event.detail.split(":")[0]} · tool rejected`
            : "Tool event · details withheld";
        break;
      case "blocked": label = "Authorization / safety policy blocked execution"; break;
      case "error": label = "Execution error · details withheld"; break;
      default: label = "Unrecognized event · details withheld";
    }
    return { index, label, elapsedMs: safeCount(event.elapsedMs) };
  }).sort((a, b) => (a.elapsedMs ?? Infinity) - (b.elapsedMs ?? Infinity) || a.index - b.index);
}

export function safeCount(value: number | null) {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

export function traceIdentifiers(traceId: string | null, sessionLabel: string | null) {
  return {
    traceId: traceId && /^[a-f0-9]{32}$/.test(traceId) ? traceId : null,
    sessionLabel: sessionLabel && /^workshop-[a-f0-9]{24}$/.test(sessionLabel) ? sessionLabel : null,
  };
}