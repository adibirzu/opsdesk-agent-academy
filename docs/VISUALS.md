# Agent relationship visuals

The diagrams use the course's existing warm-stone surfaces, red emphasis, green
runtime/context accents and Georgia headings. No copied brand photographs, source
video frames, new font downloads or additional third-party scripts are included.
The existing pinned D3 7.9.0 distribution renders the original SVG work.

## Reading path and semantics

The component map explains a controlled runtime, not infrastructure placement or
formal UML. Directed edges carry requests, proposals, context and observations.
Dashed edges distinguish optional retrieval and telemetry. Selected-step emphasis
encodes a teaching state, never traffic, confidence, model reasoning or acceptance.
The app, harness, model, tool registry, retriever, knowledge source and observer
have distinct jobs. RAG is explicitly absent from the verified Lovable baseline.

The second chart uses event timestamps from one actual browser-inspected synthetic
run: total 5,218 ms; generation 1 from 489 to 1,832 ms; both tool observations at
1,832 ms; generation 2 from 1,832 to 5,218 ms. Tools are point events because their
individual durations were not measured. The 952-token count is reported usage;
there is no sourced price or accepted billing/telemetry readback.

## Implementation contract

- One D3 component-map instance per relevant page; the standalone relationship
  page also contains one small timing chart. There is no force simulation,
  continuous animation, remote request, model call or persistent browser storage.
- Static curated node/edge data stays separate from geometry, rendering and
  interaction. D3 owns only each SVG island and its local explanatory panel.
- Container ResizeObserver selects a wide collaboration layout or a portrait
  layout with readable labels. The inspector moves below the graph on smaller
  screens. It does not shrink a wide diagram to unreadable mobile text.
- Scenario and step controls have at least 44px touch height. Every component is
  keyboard focusable with Enter/Space activation, visible focus and a persistent
  detail panel. Essential explanation never depends on hover.
- The standalone page stores only an allowlisted scenario in the URL; it preserves
  other query parameters. Other diagram instances keep ephemeral local state.
  Reset returns to step one. No cookies, analytics or learner notes are collected.
- Borders/fills can transition briefly after a user action. Reduced-motion removes
  that transition. No auto-play, particle effects or implied model activity.
- The basic text explanation remains available without JavaScript. Inspect actual
  source/tests and provider receipts to verify execution; the drawing cannot do it.

## Verify after edits

Run `node --check workshops/app-first/agent-map.js`, the public-site tests and
`test_agent_map.py`. Test all three scenarios, step bounds, component selection,
keyboard activation, URL restoration, mobile portrait and reset in a real browser.
Verify the RAG caveat and observed-run provenance remain visible. Refresh the
bounded docs export and inspect both source and pixels before publication.
