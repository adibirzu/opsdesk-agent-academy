# Student delivery through GitHub Pages

The site is static: lessons, copyable prompts, D3 explorers, tool links and the ticket preview work without a backend. The preview never generates AI answers or telemetry. Each learner builds an app and configures a separate server runtime with their own model and observability credentials. Do not connect a public guide directly to a privileged local server.

## Build and preview the selected public artifact

From the repository root, with Python 3.12:

```sh
python scripts/build_app_first_workshop.py
python scripts/build_training_course.py
python scripts/build_student_site.py --output /tmp/opsdesk-student-site
python -m http.server 8780 --bind 127.0.0.1 --directory /tmp/opsdesk-student-site
```

Use a fresh output path for each export. The exporter refuses an existing directory. Open http://127.0.0.1:8780/ and test the builder selector, copy buttons, six lessons, diagrams and ticket preview. All local references are relative, so a repository project-site prefix works.

The exporter copies an explicit file list, never the entire repository. It excludes runtime keys, private endpoints, raw receipts and unreviewed screenshots, copied Oracle photographs, logos, mosaics and design-system files. The public theme and D3 teaching diagrams are original workshop work; the pinned D3 distribution includes its license. Markdown reference links are downloadable source documents.

## Publish after repository review

Before changing repository visibility, audit the entire Git history and tracked files separately. A safe site export does not make the repository or its history safe to publish. Review source, rights, secrets, private endpoints and infrastructure identifiers before publication.

Once the reviewed source is approved for publication, choose **Settings → Pages → Source: GitHub Actions**. The manual `Student workshop Pages` workflow builds the bounded export, uploads only that directory, and deploys it. Trigger it from Actions; it does not run on every push. The GitHub-provided deployment URL is authoritative; do not hardcode an account-specific URL in the guide.

No publication, repository-visibility change or backend deployment is performed by the local exporter. Public HTTPS Pages and a local HTTP API are separate origins: mixed content and authentication require a deliberate backend design. Keep model and telemetry keys on the server.

Only the three explicitly selected, pixel-reviewed synthetic app screenshots in EVIDENCE.json are included. Their hashes are checked by the public export gate. No presenter application, model endpoint or credentials are embedded.
