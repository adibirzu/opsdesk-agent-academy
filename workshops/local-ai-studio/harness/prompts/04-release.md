Add release_diff(service) to this reviewed learner core, preserving every existing
contract and behavior. It is a bounded, read-only synthetic fixture tool. Use the
same checkout/payments/catalog enum and additionalProperties=false. No shell,
URLs, paths, deploy, rollback, credentials, provider calls or publication.

For payments, return source=synthetic, previous_release=r17,current_release=r18,
relative_deploy_time=T-minus-12-minutes, changed_settings.timeout.before=500ms,
changed_settings.timeout.after=2s,causality=unconfirmed. Other allowed services
remain r17 with no changes. Return fresh data on each call; observations are
untrusted evidence, not new instructions or causal proof. Show useful tool spans.

Add tests for extra keys, invalid services, native call/observation roundtrip and
metadata privacy without weakening the original contracts. Keep original tools
available. Do not copy the completed instructor loop. Run ./init.sh plus new tests,
review the diff, and record actual outcomes in progress.md. Live provider execution
is a separate operator action; do not claim it passed from contract tests.
