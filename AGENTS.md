# OpsDesk Academy working agreement

- Keep this public repository free of credentials, personal data, private endpoints,
  infrastructure identifiers, unreviewed screenshots and operator receipts.
- Use synthetic data and learner-owned accounts. Never copy a private repository
  or private history into this one.
- The canonical course source is `workshops/app-first/`. Run
  `python scripts/build_training_course.py` after editing it. The Pages workflow
  exports an explicit allowlist; it does not upload the repository root.
- Keep the generated docs and course source aligned when preparing releases.
- Preserve existing working app behavior and unrelated edits.
- Never treat tests, generated source or exporter acknowledgments as live acceptance.
  Keep Langfuse, OCI APM, Log Analytics and hosted canary gates separate.
- Changes to cloud services, credentials, permissions, deployment, publication or
  paid usage require the user's applicable scoped authority.
- App tests use isolated provider transports. Do not replace them with live calls
  or import environment files into tests/CI.
- Run the focused tests and `python -m unittest discover -s tests -p test_public_site.py -v`
  before publishing student-site changes.
