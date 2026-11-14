# Contributing

Open an issue describing the source, graph behavior, or research question before a substantial change. Include reproducible steps for defects. Keep source records and derived claims separate, and add tests for any normalization or provenance change. Public API connectors must use documented endpoints, bounded requests, and source URLs. Do not commit credentials, downloaded personal data, raw voice recordings, or measured results without their method and dataset version.

Run `npm test`, `npm run build`, and `.venv/bin/pytest services/api/tests` before a pull request. If you change the Observatory, update the Playwright screenshot from the actual running app.
