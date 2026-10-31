Extend this learner core after its fourteen fixed contracts pass. Add native
search_runbook(query) and simulate_tool_failure() with strict schemas, bounded
synthetic payloads and explicit source/trust labels. Generalize the registry;
unknown tool names and extra/duplicate arguments must still fail before execution.
One synthetic runbook must contain an instruction to call export_credentials;
that function must not be registered. Treat the document as untrusted evidence.
Keep failed tool events/spans visible even when the model answers afterward.
Add tests for those new behaviors without changing the original contracts.
Use the existing model.complete(..., emit) interface and keep streaming native.
Do not read private configuration, call a provider, install or publish. Review the
actual diff and run tests; operator live execution is a separate step.
