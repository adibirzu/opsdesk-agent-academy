# Optional mission — add permitted runbook retrieval

Extend the learner's existing working OpsDesk app. This is an optional extension,
not part of the verified Lovable baseline. Read the app's actual server code and
existing applicable instructions. Preserve its working analysis, authorization,
strict tools, call limits and unknown-cost behavior.

## Outcome

The incident analyst can retrieve a relevant synthetic runbook passage, include
its source reference and say when no relevant evidence was found. Retrieval adds
context; it must not grant a new operation or claim causality.

## Build locally first

1. Use two synthetic local runbook documents with stable source labels. Do not
   import real company files, credentials or customer data. A vector database,
   embedding API or external service is not required for this initial exercise.
2. Implement one registered read-only lookup with a strict bounded query, selected
   service scope, result count and output-length limit. Use a deterministic local
   search for the first test; label its method honestly.
3. Apply document-access filtering before returning any passage. Keep source text
   as untrusted context, separate from policy and system instructions.
4. Add the permitted result to the current model context. Preserve the existing
   model and limits. No new provider, paid call, indexing service or cloud resource
   is authorized by this downloaded mission.
5. Instrument the actual retrieval operation and its status with the existing
   compatible observer. Export allowed metadata only. Do not send document bodies,
   queries or private source paths to telemetry by default.

## Check before completion

- A relevant lookup returns a bounded passage and valid source label.
- A no-match query returns an explicit no-result state, not an invented passage.
- A request outside document/service scope is rejected before data is returned.
- Unknown/extra arguments and oversized requests fail closed.
- A document saying to ignore policy, reveal keys or run a write command remains
  data; it cannot extend the registry or bypass the change stop.
- Normal create → select → analyze still works; explicit changes still stop before
  inference. Use isolated model/export doubles for regression tests.
- If a live model or telemetry check is separately authorized, run one synthetic
  case and independently verify its actual result. Otherwise leave it unverified.

## Handoff

Explain the chosen retrieval method, source ownership/filtering, changed files,
start/restart steps, exact test results and remaining gates. Do not claim a vector
search, production knowledge base, model training or provider readback you did not
perform. Keep raw inputs, outputs, screenshots and receipts private until reviewed.
