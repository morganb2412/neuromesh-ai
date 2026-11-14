# NeuroMesh AI

NeuroMesh AI is an open source research workbench for tracing public AI research, funding, models, and software through a 3D evidence graph. It asks how research growth relates to public investment, open source implementation, and documented adoption; it does not treat a search match as proof of a relationship.

![NeuroMesh AI Observatory](docs/screenshots/observatory-home.png)

The screenshot is from the running React and FastAPI application. It shows 32 public records collected in a bounded local sync and a separately labeled demonstration graph used to exercise the visualization.

## Current implementation

The Observatory renders animated WebGL points, typed edges, directional particles, camera controls, search, category filtering, selection, and a procedural shadow hologram. The assistant accepts typed questions and streams actual backend retrieval events over Server-Sent Events; matched records light up in the graph and source links appear in the answer. Browser speech recognition and speech synthesis are available where supported, with explicit microphone activation, mute, interruption, volume, and word-boundary-driven jaw motion. The avatar and voice path need more rigorous timing validation before release claims about speech synchronization.

The API stores original public records, normalized entities, evidence, edges, ingestion jobs, and investigations in SQLite for local development. OpenAlex, GitHub, Hugging Face, and NIH RePORTER connectors use documented public APIs, bounded page sizes, and source URLs. An authenticated admin endpoint starts syncs. Public investigation calls use local evidence retrieval and have an in-memory rate limit. A configured Google ADK agent may synthesize from a bounded evidence catalog only when an operator supplies an admin token, model, and credentials. No provider model call is made by default.

## Architecture

```text
Public APIs → bounded connectors → source records + evidence → entities / verified title edges
                                                      ↓
React + Three.js ← JSON graph + SSE events ← FastAPI research service
                                     ↘ deterministic graph analytics
                                      ↘ optional, admin-only Google ADK synthesis
```

See [system architecture](docs/architecture/system.md) for the data path and trust boundaries. The intended production architecture is Cloud Run, Cloud SQL PostgreSQL with pgvector, Cloud Storage, Cloud Run Jobs, Pub/Sub, Scheduler, Secret Manager, and Vertex AI. The present code is a local prototype; the included Terraform is a Cloud Run API preview and does not provide durable persistence.

## Stack

React 19, TypeScript, Vite, React Three Fiber, Three.js, Tailwind CSS, ECharts, FastAPI, SQLite, NetworkX, optional Google ADK, Vitest, Pytest, and Playwright. The main scene uses buffer geometry for entity points, lines, and moving edge particles, plus instanced hit targets. It pauses rendering updates in hidden tabs and honors reduced motion preferences.

## Sources and graph semantics

| Source | Record type | Current connector |
| --- | --- | --- |
| [OpenAlex](https://docs.openalex.org/) | Publications | Works search |
| [GitHub](https://docs.github.com/en/rest/search) | Repositories | Repository search |
| [Hugging Face Hub](https://huggingface.co/docs/hub/api) | Models | Public models API |
| [NIH RePORTER](https://api.reporter.nih.gov/) | Public awards | Project search v2 |

Entities have an ID, type, label, source record, and demo flag. Relationships have a type, confidence class, optional evidence ID, and demo flag. The current extractor creates a `MENTIONS` edge only when a record title literally contains the collection query. That edge is `verified` against a source URL. Search results without a literal match remain unconnected records. Demo edges are marked `similarity` and carry no evidence. Future extractors must preserve the distinction among verified, extracted, inferred, and semantic edges.

## Agent orchestration and analysis

The research endpoint emits `investigation.started`, `agent.activated`, `query.planned`, `source.search.*`, `entity.matched`, `graph.path.selected`, `analysis.*`, `response.streaming`, and `investigation.completed` events during actual execution. The default answer is deterministic and explicitly limits its claims. The optional ADK path is configured with a bounded `get_evidence` tool and instructions to cite exact URLs and reject instructions embedded in source text. Agent retries, traces, cost accounting, and a full specialist team remain future work.

`GET /api/analytics` computes connected components, density, and PageRank by deterministic power iteration. It excludes demo nodes by default. This is graph structure analysis, not a result about the primary research question. The [research protocol](docs/research/methodology.md) prespecifies the 2023–2026 hypothesis, lag windows, indicators, missingness checks, and confidence interval plan.

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

Open `http://127.0.0.1:5173`. The API starts with a clearly labeled seeded graph. To collect public records locally without credentials:

```bash
.venv/bin/python scripts/sync_public.py --query 'artificial intelligence' --limit 8
```

The script makes at most one bounded request to each of four public APIs and persists original payloads and URLs in `data/neuromesh.db`, which is ignored by Git. To use the admin HTTP sync endpoint, set a long `NEUROMESH_ADMIN_TOKEN` outside the repository and pass it in `X-Admin-Token`. To enable ADK synthesis, also configure `NEUROMESH_ENABLE_ADK=true`, `NEUROMESH_MODEL`, and supported Google credentials. Anonymous visitors cannot trigger model calls.

## Google Cloud deployment

The preview Dockerfile and Terraform module are in `services/api` and `infrastructure/terraform`. They define one capped Cloud Run API instance in `us-central1`, with ADK disabled. This preview uses ephemeral SQLite and is unsuitable for retained research data. A production deployment requires Cloud SQL integration and migrations, a frontend service, service identities, Secret Manager bindings, scheduled ingestion, and a durable rate limiter. No cloud resource is created by this repository. Review the [cost gate](docs/architecture/costs.md) before enabling billing; the minimum persistent Cloud SQL compute scenario is about $7.67/month before storage and other services.

## Testing and observed results

```bash
npm run build
npm test
.venv/bin/pytest -q services/api/tests
npm run test:e2e  # with both development servers running
node scripts/capture_observatory.mjs
```

The initial local sync returned eight records from each of the four sources. Browser verification confirmed the homepage, both WebGL canvases, a completed investigation event stream, and zero page errors during screenshot capture. Backend tests cover demo separation, admin gating, citation provenance, bounded investigation behavior, and repeatable graph metrics. These are engineering checks; **the primary scientific experiment has not been run**, so there are no reported correlations or model benchmark results.

## Limitations and next work

The research, LLM Lab, Experiments, Agents, Pipelines, Analytics, and Reports tabs are navigation scaffolds; the Observatory is the implemented workbench. Search is lexical over a small local index. The 3D layout is a seeded cluster and spring simulation; larger graph layout, drag interactions, temporal snapshots, camera guided traversal, and stronger level of detail are pending. Browser speech APIs vary by platform, and word boundaries are not phoneme or amplitude data. The full Google Cloud speech pipeline, durable Postgres and pgvector store, broader ingestion catalog, entity resolution, multi-agent ADK workflow, reproducible primary study, and provider evaluation lab are not implemented.

The next milestone is durable data and richer evidence extraction, followed by voice timing and agent orchestration. No research claim should be published until the prespecified experiment is executed and reviewed.
