# Actual Lovable rehearsal app — sanitized source

This is the generated TypeScript/TanStack Start OpsDesk app used in the reviewed
synthetic rehearsal. Environment files, presenter bindings, private editor URLs
and raw receipts are excluded. GitHub Pages cannot run this server application.

## Easiest route

Create your own Lovable project using the course's [rehearsal recipe](../docs/APP-REHEARSAL.md)
and prompts. Review backend activation, then sign in to your generated app. Keep
your available native model and authenticated server integration. Your runtime
may differ from this snapshot.

## Inspect and test

Use an existing supported Node/Bun toolchain. Read package.json first:

```sh
bun install --ignore-scripts --frozen-lockfile
bun run test
```

All 17 tests passed on the downloaded source using isolated model/export
transports, without real model or telemetry keys. They cover change stops,
strict schemas, scoped tools, denied rate reservations, durable provider denial,
bounded calls, metadata filtering, missing/rejected configuration, partial export
and routing. They do not prove live authentication, billing or trace readback.

Running the generated app additionally needs your own supported Cloud/auth/database
and managed native model configuration. Inspect `src/integrations`,
`src/lib/*.functions.ts`, `src/lib/*.server.ts` and server middleware for required
environment references. Supply values only in your own server settings. No working
project credentials are included. An unconfigured local preview is not a working
authenticated AI deployment.

## Read the harness

- `src/lib/opsdesk-contract.ts`: strict input/tool contracts and change classification.
- `src/lib/opsdesk-agent.server.ts`: early change stop, bounded model calls and synthetic tools.
- Authenticated server wrappers and middleware: app session and per-account quota storage.
- `src/lib/langfuse.server.ts`: isolated OpenTelemetry provider, metadata allowlist and bounded OTLP export.
- `src/test/`: isolated safety, exporter and routing checks.

After compatible instrumentation exists, connect Langfuse with only
`LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in server secrets.
The UI distinguishes exporter status from independent readback. Never place keys
in client variables or builder chat.

This snapshot is a starting point, not production security certification. Preserve
unknown-cost and synthetic-data labels. Do not enable unprotected inference,
automatic retries, arbitrary tools or wider permissions to make a test pass.
