# Build a visible app. Add AI. Follow one action.

A simpler 60-minute workshop. Pick **one** of Base44, v0, Lovable or Codex. Describe OpsDesk,
click the generated incident board, then add its agent, observability and a hosting
walkthrough. Participants do not build an HTTP server or agent harness from scratch.

Open [the visual guide](index.html), copy [the app prompt](prompts/01-build-app.md)
and use [the builder notes](BUILDERS.md). The authored local reference is available
at `http://127.0.0.1:8770/desk` after starting the existing Studio server.

| Minutes | Do | Required result |
|---|---|---|
|00–05|Define the app|One useful incident investigation|
|05–25|Build in the chosen platform|Create/search/filter/select tickets|
|25–45|Connect the real agent|Actual selected-ticket model/tool answer|
|45–50|Run the end-to-end journey|Ticket creation through AI answer|
|50–55|Test loading and failure|No stuck busy state or fake success|
|55–60|Save and restart the baseline|Repeatable start/stop and handoff|

Start with synthetic data and your own builder account. Confirm your account's
credits and backend capabilities before the event; this lab buys nothing, creates
no SaaS project and promises no free entitlement. First inspect the preview:
create a ticket, search for it, filter and open it. The initial AI state must say
it is disconnected. A working UI is a useful first checkpoint, not AI acceptance.

The [local reference](APP-CAPABILITIES.md) reuses the existing instrumented agent.
It is authored workshop code, not proof that one of the SaaS platforms generated
it. See [API-CONTRACT.md](API-CONTRACT.md), [OTEL-LANGFUSE.md](OTEL-LANGFUSE.md) and
[OCI-HOSTING.md](OCI-HOSTING.md) for the prepared backstage setup. These are
facilitator material; keep the participant's first screen focused on the app.

Run locally with an existing Python 3.12+ environment:

```sh
uv sync --frozen --extra studio
mkdir -p local/private/app-first
cp workshops/local-ai-studio/studio.example.toml local/private/app-first/studio.toml
chmod 600 local/private/app-first/studio.toml
# Edit the private file with your exact real model alias and approved endpoint.
PYTHONPATH=src .venv/bin/python -m agent_workshop.studio \
  --config local/private/app-first/studio.toml \
  --output "local/private/app-first/run-$(date +%Y%m%d-%H%M%S)" --port 8770
```

Optional server keys use `--secrets /private/path/keys.env` with mode 0600. Configure
your own Langfuse destination, never the facilitator's project keys. Open `/desk`.
A page load, ticket creation or filter action makes no model call. Analyze safely
uses real inference; Test a change request exercises the zero-model policy path.
A model/export error stays explicit. Nothing becomes a scripted reply.

The earlier [core-first course](../local-ai-studio/README.md) remains optional
advanced material. Do not require it or run three builders in the same hour.

## Learn the system on the page

The Redwood edition adds [Agent basics · agent basics](meet-your-agent.html) and
[Inside the harness · harness walkthrough](inside-the-engine.html), with the previously reviewed Oracle
source figures, original D3 teaching diagrams and inline backend explanations.
The main guide now includes these explanations directly instead of requiring
facilitator detail pages for the core lesson.

The **Codex** build tab contains a local creation prompt and an OCI preparation
prompt. It helps produce an app and a reviewable hosting packet; no button runs
shell commands, model requests or deployment actions. See REFERENCES.md for
source attribution, local dependency licences and Oracle asset restrictions.

## Student web edition

Use [GitHub Pages delivery](PAGES.md) for the bounded static export, manual deployment workflow and publication review. The [interactive preview](preview.html) works without credentials. The guide includes official tool links and self-reported lesson checkpoints. A static preview does not run the agent.

## Continue as a six-part online course

The one-hour workshop is Part 1. [OpsDesk Academy](course.html) adds five one-hour labs: the agent engine; models and cost; end-to-end evidence; security and failure; and OCI release preparation. Start with [setup and help](help.html), use the [workbook](WORKBOOK.md), and consult the [delivery checklist](DELIVERY-CHECKLIST.md) for recording and assessment. The [Meet your AI teammate](meet-your-agent.html) and [Inside the agent engine](inside-the-engine.html) primers keep the explanations approachable without age labels.

## Agent handoff for every part

Each course part provides a generated Markdown agent brief with prerequisites, starting state, the new capability, implementation tasks, commands/prompts, troubleshooting, completion gates and a result record. The on-page download appends learner notes locally as Markdown; those notes are untrusted context, not higher-priority instructions. All six briefs are also available as direct `.md` downloads.

Part 1 requires a working app and an actual model/tool-backed AI action. A disconnected preview or provider failure does not complete it. Prepare the chosen model before the hour. Later parts extend the same baseline rather than replacing it; observability and cloud hosting move to their dedicated parts.

## Follow one incident through the course

The shared payments-latency case connects all six parts. Each part includes a local D3 explanation with useful/stop paths, three short Q&As and links to its next reference. Part 3 includes an illustrative token-cost calculator with an explicit unknown state. These interactions teach the workflow; they perform no provider calls or telemetry export. Use actual app receipts for completion. The questions and answers are included in each Markdown agent brief.

## Repeat everything independently

Use [Run it at home](replicate.html) for the tool/install/account matrix, pinned local setup, model configuration, restart and troubleshooting. The read-only `scripts/course_doctor.py --part N` checks local prerequisites without touching secrets or cloud resources. The [Langfuse lab](langfuse.html) covers your own installation/project, private configuration, OTel export and independent trace readback. The [guardrail map](GUARDRAILS.md) separates implemented boundaries from production gaps. These links are also visible in the course navigation and the agent lesson.

## Three learner workflows

[Choose a persona](personas.html): business/C-level browser-first; IT with basic AI guided implementation; IT with AI knowledge engineering depth. Each has six tailored workflows, explanatory links and a separate Markdown brief per part. The same app and real-AI finish line apply to all three. Technical reference tasks are optional for the browser route.

Local proof can be reproduced with `.venv/bin/python scripts/rehearse_personas.py --output local/private/my-persona-rehearsal`. It runs a reviewed allowlist of isolated contract tests, not arbitrary deployment scripts, model calls or cloud mutations. Its receipt explicitly separates local contracts from SaaS generation, live AI and telemetry acceptance.

## Read the agent trace

After the app works, [connect Langfuse](langfuse.html), then complete
[Follow one agent run](langfuse-basics.html). Download the full
[agent instructions](LANGFUSE-BASICS.md). The recorded trace screenshots contain
no account or private project identifiers.

## Keep the same app across all six parts

Use the six-part strip on each lesson to follow **working app → agent engine →
models and cost → traces → security → cloud handoff**. The header keeps the main
route visible; **Labs & help** groups supporting exercises and references.

Each lesson and every persona’s Markdown agent brief includes an app continuity
checkpoint. Reopen the same learner-owned project, preserve a private baseline
reference, add the new capability, and repeat previous acceptance checks. Keep a
private handoff note with observed results, missing evidence and the next action.
Changing persona changes the learning route; it does not create another app.
Current reference ticket state resets on reload. Re-create synthetic fixtures;
persistent storage is not an accepted capability. OCI deployment and provider
telemetry readback remain separate, explicit acceptance gates.


## Open the session, then watch and build along

Use [the opening poll](poll.html) for a two-minute conversation about AI
experience, frequency, desired outcome and preferred demonstration style. Its live
card opens the selected anonymous Google Forms workshop poll. The configured
form does not collect email or require sign-in. Answers submitted there are handled
by Google Forms; the presenter opens its actual response summary. The course does
not invent or compute shared response counts. Optional private practice remains in
the current tab and is not submitted to the live form; learners may download only
those private practice choices as JSON. The [Q&A page](qa.html) currently uses the
optional final question in the same workshop form. No private owner/editor URL is
stored in public configuration.

[Watch and follow along](watchalong.html) provides a continuous 45-minute chapter
plan, prepared narration summaries, matching lesson links, copyable prompts and
manual tasks beneath the video area. Eight selected task videos and their exact
narration transcripts are available. They are edited narrated checkpoints with
labelled practice intervals, not a continuous screen recording. Current evidence labels keep
historical Lovable/Langfuse acceptance separate from new v0/Base44 rehearsal gates.
A learner can open the matching local MP4/WebM/MOV in the page without uploading
it. Seeking is enabled only after playable video metadata loads.

The canonical schedule and release status are in `watchalong.json`. To release a
video, first review all frames/audio for private data, provide exact captions and
transcript, add only the selected reviewed media to the explicit export allowlist,
and update the manifest. Do not point the site at private recordings or unreviewed
remote URLs. The downloadable [watch-along guide](WATCHALONG-GUIDE.md) works before
the recording is released. The [Codex/CLI demo](CODEX-CLI-DEMO.md) has its own
execution and provider-acceptance boundaries.


### Task-sized video playback

The published route uses one player and an ordered playlist of small task videos.
The first chapter never autoplays on page load. After the learner presses Play,
its `ended` event opens the next released chapter and attempts playback once.
If browser autoplay policy rejects that transition, the page shows **Play this
chapter** and waits for the learner. It never retries automatically or skips an
unreleased chapter. Chapter buttons load the relevant clip paused, while the page
maps its local playback time onto the global 45-minute schedule. A selected local
full-length file is a separate mode; it is neither uploaded nor mixed into the
published playlist.

Each chapter has optional `media` metadata in `watchalong.json`: `src`, `captions`,
`transcript_file` and `reviewed`. Keep paths null and `reviewed: false` until the
specific video, audio, captions and transcript have passed review. Release requires
all three existing relative asset paths plus the reviewed flag; add those exact
files to the public export allowlist separately. Captions use **chapter-local**
timestamps. The generator displays the literal transcript file under **Recorded
transcript** only for released media; all remaining text stays labelled **Prepared
narration summary**. The availability count prevents a partial playlist from
appearing to be the full finished recording.


Selected task-video entries in `EVIDENCE.json` bind the reviewed MP4 hash and
pixel review to an explicit `audio_qa` object. The object records full-stream
decode, narration/VTT correspondence, caption-timing verification, whether a
human listened, and the actual review scope. Passing technical audio QA must not
be described as a full human listening review. Unperformed listening stays false;
export does not silently upgrade that evidence class.
