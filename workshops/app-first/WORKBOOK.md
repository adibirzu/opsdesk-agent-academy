# OpsDesk course workbook

Use synthetic inputs. Keep raw receipts, recordings and credentials private.

A task checkbox is self-reported. Provider acceptance needs actual independent readback.

## Part 1: From idea to a working app

A working OpsDesk app: create/search/filter/select tickets, run one real AI investigation, show honest loading/errors, and restart it from written instructions.

- [ ] Define the useful action
  Expected: Explain the difference between UI, model and agent in your own words.
  My result / evidence reference: ____________________

- [ ] Build the visible inbox
  Expected: All four interactions work and the AI state is disconnected.
  My result / evidence reference: ____________________

- [ ] Connect one agent action
  Expected: The selected ticket produces an actual model/tool answer in the app. A provider failure is a blocker to fix, not first-hour completion.
  My result / evidence reference: ____________________

- [ ] Verify the complete user journey
  Expected: The real app completes ticket creation → selection → AI answer.
  My result / evidence reference: ____________________

- [ ] Test loading and failure states
  Expected: No spinner stays stuck and no canned answer masks a failed provider.
  My result / evidence reference: ____________________

- [ ] Save the working baseline
  Expected: Another learner can restart this scoped app and reproduce its AI action with their own model.
  My result / evidence reference: ____________________

## Part 2: Upgrade your app’s agent engine

Your own agent core, a reviewed tool registry and passing behavioral contracts.

- [ ] Open a fresh learner workspace
  Expected: You can identify the model, tool and observer interfaces.
  My result / evidence reference: ____________________

- [ ] Ask Codex for the smallest loop
  Expected: The core returns an answer or an explicit terminal failure; it cannot run shell commands.
  My result / evidence reference: ____________________

- [ ] Make the tools deliberately small
  Expected: Valid calls reach one handler; invalid calls do not execute a handler.
  My result / evidence reference: ____________________

- [ ] Walk through an observation
  Expected: The fixed contracts pass and the original app still completes a real investigation through the new engine.
  My result / evidence reference: ____________________

## Part 3: Connect models. Know the cost.

One real model run, a capability record and a cost estimate with explicit assumptions.

- [ ] Bind one actual model
  Expected: Configuration names one explicit model, allowed host and output bound.
  My result / evidence reference: ____________________

- [ ] Prove one native tool round-trip
  Expected: The second task has an actual native tool call and observation; errors remain visible.
  My result / evidence reference: ____________________

- [ ] Compare behavior fairly
  Expected: Your comparison labels the exact task, returned model and known limitations.
  My result / evidence reference: ____________________

- [ ] Calculate only what is known
  Expected: A reviewer can reproduce the estimate; local GPU costs are not called zero.
  My result / evidence reference: ____________________

## Part 4: Follow every action

A trace map, one exact Langfuse readback and a documented app/log correlation path.

- [ ] Name the boundaries
  Expected: The map explains who records, exports and independently queries each signal.
  My result / evidence reference: ____________________

- [ ] Enable metadata-only OTel
  Expected: The local receipt has actual span IDs and an exporter result.
  My result / evidence reference: ____________________

- [ ] Verify the exact trace
  Expected: The expected session, generation/tool observations and exact trace are found, or the missing checkpoint is named.
  My result / evidence reference: ____________________

- [ ] Join application and log evidence
  Expected: Live acceptance requires independent readback from each configured destination. Without OCI, submit a clearly labelled correlation design.
  My result / evidence reference: ____________________

## Part 5: Make the safe path the easy path

A small threat model, negative-test evidence and a mitigation/retest record.

- [ ] Mark the trust boundaries
  Expected: Each control has a concrete code location and expected failure outcome.
  My result / evidence reference: ____________________

- [ ] Prove the change stop
  Expected: The model factory is not constructed for a change intent.
  My result / evidence reference: ____________________

- [ ] Treat hostile instructions as data
  Expected: No unregistered handler executes. Preserve the real result even if the model follows a malicious instruction in text.
  My result / evidence reference: ____________________

- [ ] Break it and explain it
  Expected: Each case has the expected terminal outcome and no cross-session data exposure.
  My result / evidence reference: ____________________

## Part 6: Give your agent a cloud home

A release packet, protocol adapter design, rollback plan and explicit acceptance matrix.

- [ ] Choose the runtime and protocol
  Expected: The design names the actual image entrypoint and supported request/response protocol.
  My result / evidence reference: ____________________

- [ ] Prepare a reviewable deployment
  Expected: A reviewer can identify the account, region, compartment, resource changes and cleanup plan without exposing private values.
  My result / evidence reference: ____________________

- [ ] Rehearse acceptance before rollout
  Expected: Acceptance records distinguish locally tested, configured and provider verified. Without a cloud target, submit the unexecuted runbook.
  My result / evidence reference: ____________________

- [ ] Hand it to the next operator
  Expected: A second operator can explain how to start, verify and stop the system without borrowing presenter credentials.
  My result / evidence reference: ____________________
