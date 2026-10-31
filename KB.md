# OpsDesk troubleshooting knowledge

## KB-001 — Export failure without an HTTP receipt needs a safe stage label

Observed: the hosted standalone preview's zero-model policy case repeatedly
returned failed telemetry with no HTTP status. Normal embedded-preview telemetry
had previously worked. These observations do not establish the root cause.

The original exporter intentionally suppressed exceptions but returned no stage
classification. Add only allowlisted failure codes: flush_error,
serialization_error, timeout, transport_error, http_error, invalid_response.
Never return raw exception messages, URLs, headers or credential-derived values.
Keep one export attempt, no automatic retries and independent readback unverified.

Regression: four isolated tests initially failed because failureCode was absent.
Timeout tests additionally revealed that DOMException need not be instanceof Error
in the test realm. Check only the bounded name property for TimeoutError/AbortError
rather than assuming realm inheritance. All 35 app tests then passed.

Status: diagnostic source locally verified; actual hosted cause and remediation
remain pending access to the signed-in builder. Do not label this as a fixed
transport failure or widen timeouts/permissions based on speculation.
