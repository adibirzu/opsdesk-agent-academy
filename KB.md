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

Resolution evidence: safe hints identified a redirect-related transport failure.
The working implementation uses manual no-follow mode, explicitly rejects any
3xx without a second request, normalizes the validated endpoint to a string and
preserves the default fetch receiver. URL normalization and receiver binding
alone did not clear the hosted symptom. The successful zero-model run returned
HTTP 200; its exact trace and session were independently matched in Langfuse with
two observations, zero generations and the expected policy metadata. No
redirect was followed. The underlying platform's redirect implementation was
not separately inspected, so do not assert a particular vendor-runtime bug.

Preview revisions can lag or remain pinned to history. Select Preview on the
newest completed change card before Open preview and verify the rendered
controls. Source downloads and build output do not establish the active runtime.
The final downloaded app suite passes 49 isolated tests.
