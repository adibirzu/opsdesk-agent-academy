Instrument the learner core with the injected Observer. Preserve its existing
contracts. Add security.authorize, generation and tool spans with correct session
and actual model attributes. Emit bounded metadata events for starts, usage,
validation, errors and completion; never prompt/answer/tool payload/key content.
Report actual usage and keep partial counts unknown while enforcing the known
lower bound. Do not invent a rate or invoice. Use explicit model-matched pricing
only if separately configured. Add tests for correlation, metadata privacy and
exporter failure. Do not call providers or edit private keys while implementing.
Do not mark backend acceptance verified; the operator must query the exact trace
and session independently through the existing readback route.
