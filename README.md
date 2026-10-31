# OpsDesk Agent Academy

Six practical parts. Three learner routes. Build one visible AI app, then add its
harness, measurements, observability, security checks and reviewed hosting plan.

- [Start the course](https://adibirzu.github.io/opsdesk-agent-academy/course.html)
- [All persona workflows](https://adibirzu.github.io/opsdesk-agent-academy/workflows.html): 18 individual Markdown briefs and three complete six-part bundles.
- [App walkthrough and expected results](https://adibirzu.github.io/opsdesk-agent-academy/showcase.html)
- [Complete Lovable demo](https://adibirzu.github.io/opsdesk-agent-academy/lovable.html): all build prompts, sign-in, acceptance steps, real screenshots and server-only Langfuse setup.
- [Interactive agent map](https://adibirzu.github.io/opsdesk-agent-academy/relationships.html): follow the app, harness, LLM, tools, optional RAG and observability; inspect the observed-run timing chart.
- [Actual rehearsal screenshots](https://adibirzu.github.io/opsdesk-agent-academy/evidence.html)
- [Simple Langfuse setup](https://adibirzu.github.io/opsdesk-agent-academy/langfuse.html)

## Choose your route

**Business/no IT:** use your own Base44, v0, Lovable or Codex account and the
downloadable builder instructions. No terminal is needed for the browser route.

**IT starter:** follow guided implementation, inspect the engine and run the local
reference with your own working model.

**AI engineer:** extend the same contracts, negative tests, tracing and deployment
readiness checks. Cloud actions require your own current authority and scope.

## Included source

`docs/` is the bounded GitHub Pages student site. `workshops/app-first/` is a
checkout copy of those lessons so downloaded workflow paths resolve locally.
`reference-app/` contains the actual Lovable-generated TypeScript app, excluding
environment files and presenter bindings. An original workshop SVG replaces its
favicon. Connect your own supported backend/auth/model environment; this source
does not give access to the presenter's runtime.

`src/agent_workshop/` is the separate local Python reference.
`workshops/local-ai-studio/studio.example.toml` is an unconfigured template.
Selected scripts and isolated tests support the local engineering exercises.
This fresh public history excludes the private operator repository and its history.

## Local engineering reference

Install Python 3.12+ and uv from their official sources. From this checkout:

```sh
uv sync --frozen --extra studio
.venv/bin/python scripts/course_doctor.py --part 1
mkdir -p local/private/part-1
cp workshops/local-ai-studio/studio.example.toml local/private/part-1/studio.toml
chmod 600 local/private/part-1/studio.toml
```

Edit the private file to your already-working tool-capable model and exact alias.
Configure keys through private environment references. Start the owned foreground app:

```sh
PYTHONPATH=src .venv/bin/python -m agent_workshop.studio --config local/private/part-1/studio.toml --output local/private/part-1/run-01 --port 8770
```

Open http://127.0.0.1:8770/desk. Ctrl-C stops that owned foreground server. The
example model is deliberately unconfigured, with no fake fallback.

For cloud-readiness tests, use `uv sync --frozen --extra live`. Tests do not deploy.
Review the exact target, permissions, cost and rollback before any cloud action.

## Actual Lovable reference and evidence

See [the reference app setup](reference-app/README.md) and
[the rehearsal recipe](docs/APP-REHEARSAL.md). Native Lovable AI was browser-verified
on synthetic data with two tools and two model calls. Its 17 isolated source tests
passed locally. An explicit change request stopped with zero model calls.

The optional Langfuse exporter is implemented and locally tested. Live ingestion
and independent readback remain pending. A live two-model comparison and this
course's new hosted capstone are not accepted yet. Exact evidence and remaining
gates appear in every part. GitHub Pages hosts lessons, not an AI backend.

## Privacy and maintenance

Use your own accounts and projects. Keep model/Langfuse keys server-side, out of
browser bundles, builder chat, Git, notes and screenshots. Only selected,
pixel-reviewed synthetic screenshots are published. Oracle video frames, internal
brand packages, private endpoints, infrastructure identifiers and raw receipts
are excluded.

Edit this public repository going forward. Edit `workshops/app-first/`, then run
`python scripts/refresh_student_docs.py` with Python 3.12+ to regenerate the checked-in
site. The pinned Pages workflow independently builds and validates its own bounded
artifact on each push to main. Keep `docs/` static and review source,
links, persona downloads, screenshots and privacy before each release. Never copy
private operator files into it. This is independent educational work, not an
official Oracle product or endorsement. Vendored D3 retains its own license;
third-party subscriptions and runtime access are not included.
