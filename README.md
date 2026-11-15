# NeuroMesh AI

NeuroMesh AI is an open source research workbench for tracing public AI research, funding, models, and software through an interactive 3D evidence graph. Its central question is how research growth relates to public investment, open source implementation, and documented adoption. A search match is never treated as proof of a relationship.

![NeuroMesh AI Observatory](docs/screenshots/observatory-home.png)

This is a Playwright screenshot of the running React and FastAPI application. It contains 32 indexed public records from a bounded local sync and a separately labeled visual demonstration layer.

## What works today

The Observatory renders an animated WebGL field, typed edges, directional particles, camera controls, search, filters, selection, a source inspector, and a procedural shadow hologram. Typed questions trigger real Server-Sent Events from indexed retrieval. Matched nodes illuminate, and answers include source links. The Research page searches indexed records; Pipelines displays actual ingestion jobs; Analytics shows live graph measurements and deterministic TF-IDF title clusters. Agents displays operator-only execution history when available. LLM Lab, Experiments, and Reports clearly report that no measured runs exist.

Browser speech recognition is available where supported after explicit microphone activation. Browser synthesis uses word-boundary timing. The optional operator-only Google Cloud Text-to-Speech path decodes generated audio in Web Audio and drives the hologram jaw from its PCM amplitude; stopping playback stops the animation. No raw microphone recording is stored by the app. Voice behavior depends on browser permissions and configured cloud access.

## Architecture

```text
Approved public APIs → bounded connectors → records, evidence, entities, typed edges
                                               ↓
React / Three.js ← graph JSON + actual SSE events ← FastAPI → PostgreSQL or SQLite
                                                   ├→ PageRank and TF-IDF analysis
                                                   ├→ operator-only ADK research → verification
                                                   └→ operator-only Cloud Text-to-Speech
```

See [system architecture](docs/architecture/system.md) for trust boundaries and storage. The Google Cloud target is one capped Cloud Run service serving the React bundle and API, backed by a dedicated Cloud SQL PostgreSQL instance, Artifact Registry, Secret Manager, and a scoped runtime service account. Terraform has been validated but **not applied**.

## Stack and graph semantics

React 19, TypeScript, Vite, React Three Fiber, Three.js, Tailwind CSS, ECharts, FastAPI, SQLite/PostgreSQL, NetworkX, Google ADK, Google Cloud Text-to-Speech, Vitest, Pytest, and Playwright. The scene uses buffer geometry and instanced hit targets, pauses updates in hidden tabs, and honors reduced motion preferences.

Each source record has an external ID, original JSON, URL, and retrieval time. Entities point to source records; relationships have a type, confidence class, optional evidence ID, and demo flag. The current extractor creates a verified `MENTIONS` edge only when a record title literally contains the collection query. Demo edges have no evidence and are never included in live analytics.

| Source | Record type | Connector |
| --- | --- | --- |
| [OpenAlex](https://docs.openalex.org/) | Publications | Works search |
| [GitHub](https://docs.github.com/en/rest/search) | Repositories | Repository search |
| [Hugging Face Hub](https://huggingface.co/docs/hub/api) | Models | Public models API |
| [NIH RePORTER](https://api.reporter.nih.gov/) | Public awards | Project search v2 |

## Agents, analytics, and research method

Public investigations use bounded local evidence retrieval. With an operator token, configured Vertex model, and explicit ADK enablement, a Google ADK research agent reads a bounded catalog and a verification agent checks its draft against that catalog. ADK execution events and token counts are recorded; model calls are limited to four per investigation, 60 seconds, and 20 investigations per day by default. Provider calls are off by default. Retrieved text is treated as data, and agent tools cannot execute commands or arbitrary SQL.

`GET /api/analytics` computes PageRank, density, and connected components on live nodes. `GET /api/clusters` builds deterministic TF-IDF vectors from source titles, joins records above a fixed cosine threshold, and returns a dataset SHA-256 fingerprint plus source URLs. Title clustering is a lexical baseline, not a scientific relationship result. The [prespecified research protocol](docs/research/methodology.md) defines the 2023–2026 hypothesis, lag windows, missingness checks, and confidence interval plan. **The primary scientific experiment has not run**, and there are no published correlations or model rankings.

## Local development

Requires Node 24 and Python 3.11+.

```bash
npm ci
python3 -m venv .venv
.venv/bin/pip install -e 'services/api[test,agents]'
.venv/bin/uvicorn neuromesh_api.main:app --host 127.0.0.1 --port 8000
# In another terminal:
npm run dev
```

Open `http://127.0.0.1:5173`. The seeded visual layer is explicitly marked as demonstration data. To index a bounded public sample:

```bash
.venv/bin/python scripts/sync_public.py --query 'artificial intelligence' --limit 8
```

The command makes one request to each of four approved public APIs. SQLite lives in ignored `data/neuromesh.db`. To use the operator HTTP endpoints, set a long `NEUROMESH_ADMIN_TOKEN` outside Git and enter it in the Observatory settings. A PostgreSQL URL can be supplied with `NEUROMESH_DATABASE_URL`. The optional `NEUROMESH_ENABLE_ADK`, `NEUROMESH_MODEL`, and `NEUROMESH_ENABLE_CLOUD_TTS` settings require Google credentials and may incur charges.

## Google Cloud deployment

Deployment is staged in [Terraform](infrastructure/terraform/main.tf). The module targets the **existing** `moesautomationweekly` project and uses new NeuroMesh-specific names. Stage one creates the image repository, runtime identity, secrets, and a dedicated 10 GiB `db-f1-micro` PostgreSQL instance. Stage two builds and deploys a single max-one-instance Cloud Run service. No existing project service or database is in Terraform state. The verified stage-one plan is **14 additions, 0 changes, 0 deletions**. A detailed runbook is in [GCP deployment](docs/architecture/gcp-deployment.md).

No GCP resources have been provisioned. Review the [monthly cost estimate and guardrails](docs/architecture/costs.md) before applying Terraform or running Cloud Build. Baseline persistent cost is estimated around $10–$15/month at low traffic, with additional usage charges. ADK and Cloud TTS default to off. Terraform state contains generated secrets and must remain private.

## Tests and observed results

```bash
npm run build
npm test
.venv/bin/pytest -q services/api/tests
npm run test:e2e       # with the local API and web servers running
node scripts/capture_observatory.mjs
```

The local four-source sync returned eight records per source. Automated checks cover API authorization, provenance, idempotent ingestion, repeatable graph metrics, deterministic title clusters, PostgreSQL integration, Observatory rendering, a cited investigation, Research navigation, and Analytics display. Playwright captured the screenshot above from the working app with zero page errors. The ADK and paid Cloud voice paths are wired but have not made paid provider calls or passed a deployed integration test.

## Limitations and next work

The graph still relies on a seeded visual layer to demonstrate density while the live index is small. Search is lexical; only literal title mentions create verified edges. The primary study, broader public connectors, source alias resolution, pgvector embeddings, scheduled jobs, historical snapshots, full experiment runner, provider comparison lab, and durable multi-turn agent context remain incomplete. Browser speech support varies; the Cloud TTS path still requires a deployed integration test. Cloud deployment and ingestion are pending the cost approval required for this project. These gaps are tracked as implementation work, not presented as research results.
