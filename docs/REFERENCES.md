# Sources, illustrations and asset notices

This workshop combines original teaching text/code with explicitly attributed
reference material. An illustration, source figure or example duration is not
proof of a live model call, successful export or cloud deployment.

## D3 selection

The linked [awesome-d3 catalogue](https://github.com/wbkd/awesome-d3) is useful for
finding chart and interaction families. It is not a licence for every project in
its list. The [Learn D3 introduction](https://observablehq.com/@d3/learn-d3) and
[official getting-started guide](https://d3js.org/getting-started) informed the small
select/data-join/scale/axis approach used here.

We implemented original diagrams instead of copying a third-party notebook or
installing a broad plugin stack:

- Stepped agent loop: predictable stages, no automatic playback or model requests.
- Harness component tree: choose a component and read its actual code boundary.
- Trace waterfall: select normal, failed-source or zero-generation policy examples.
  Durations are invented and explicitly labelled as illustrations.

The [OpenDesign D3 skill entry](https://github.com/nexu-io/open-design/blob/main/skills/d3-visualization/SKILL.md)
was inspected. It is a catalogue pointer to an upstream bundle, not a complete
installed implementation. Its installation commands were not executed. No global
skill, chart service, CDN runtime dependency or account connection was added.

D3 7.9.0 is served locally from vendor/d3-7.9.0.min.js. Its copyright/permission
notice is retained in vendor/D3-LICENSE. The guide uses no D3 fetch operation or
external renderer. The local library and authored explorer code require no model.

## Oracle source figures and Redwood

The two Oracle figures were previously extracted, reviewed and selected for this
workshop. Their original pixels are preserved:

- Agent loop: [Oracle video at126seconds](https://www.youtube.com/watch?v=DdKfGa_DDk8&t=126s).
- Framework/harness comparison: [Oracle video at261seconds](https://www.youtube.com/watch?v=DdKfGa_DDk8&t=261s).

The user authorized reuse of the existing Oracle material for the workshop.
These files and selected brand assets are intended for the authorized local
presentation. This work does not grant unrestricted public redistribution of
Oracle branding, source media or the full skill package. Nothing is published by
the local guide generator. Review selected assets again before Git publication.

The installed oracle-redwood-design skill supplies the linked styles.css token
entrypoint, colours/typography/spacing/base rules, red wordmark and stone mosaic.
Only its fonts.css is adapted to serve a local Figtree file rather than fetching
Google Fonts. Georgia is the display face. Figtree is supplied under SIL OFL;
redwood/fonts/OFL.txt retains its licence. ASSET-PROVENANCE.json records hashes
and source URLs for the selected assets and vendored dependencies.

## Implementation boundaries

The existing local native-tool runtime and hosted JSON/LangGraph sample are
separate adapters. The Codex prompts explain that boundary and prepare a concrete
OCI review packet; they do not execute deployment. Consult OCI-HOSTING.md for
primary service documentation and the exact remaining acceptance checks.
