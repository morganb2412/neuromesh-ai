# Architecture audit — 2026-11-16

Scope: current `neuromesh-ai` worktree, including the uncommitted 3D head rebuild. The Cloud Run deployment was **not** changed during this audit. A read-only Cloud Run inspection is currently blocked by expired Google CLI reauthentication; the last successful Terraform plan showed the existing service on image digest `aff2cc1e…`. No repository push or visibility change is part of this work.

The table and risk inventory below record the **starting state**. The gate checklist and validation notes track changes made afterward; do not read the initial gaps as current implementation claims.

## Current system

| Area | Implemented | Gap or risk |
| --- | --- | --- |
| Web | React 19, TypeScript, Vite, R3F/Three.js, ECharts; Observatory, Research, LLM Lab, Experiments, Agents, Pipelines, Analytics, Reports | LLM Lab, Experiments, and Reports are honest placeholder pages. No durable conversation session. |
| Graph | BufferGeometry point/edge rendering, force motion, search, kind/edge filters, node inspector, selection, SSE highlighting | Real citation/author/institution graph is absent. Camera focus computes initial rather than current position. 144 seeded nodes and edges still appear beside real records. |
| Face and voice | CC0 MakeHuman-derived 3D mesh, quad-grid shader, integrated eyes, state-driven motion; browser speech input/output; operator-only Cloud TTS with PCM-driven jaw | Browser speech uses word boundaries as approximate jaw timing. Physical microphone behavior depends on Chrome. The uncommitted mesh release is local only. |
| API | FastAPI, typed input bounds, `/api/health`, `/api/graph`, `/api/status`, `/api/analytics`, `/api/clusters`, `/api/investigate`, operator-only `/api/admin/sync`, `/api/speech`, `/api/agent-executions` | Unauthenticated investigation rate limit is process-local. No source-specific research API, incremental checkpoints, or durable session API. |
| Storage | SQLite locally and Cloud SQL PostgreSQL through a small SQL adapter; raw source JSON, entities, evidence, relationships, jobs, investigations, usage and agent executions | Schemas diverge; no versioned migration system. Scholarly identifiers/authors/institutions/license/validation fields are missing. Failed sync retains prior rows but UI does not clearly expose last verified snapshot. |
| Ingestion | Bounded OpenAlex, GitHub, Hugging Face, NIH API calls with job status and idempotent record upsert | OpenAlex selects only five fields and drops scholarly authorship/citation/topic metadata. No arXiv/PubMed connector, retry policy, pagination checkpoint, validation quarantine, or dead-letter report. |
| Agents | Operator-only Google ADK research and verification pair, bounded model calls, execution trace and token usage | The public path is deterministic lexical retrieval. Agent sessions are in memory. Specialized discovery, normalization and graph agents are not present. |
| Cloud/security | Existing `moesautomationweekly` Cloud Run, Cloud SQL, Artifact Registry, Secret Manager, Terraform; operator token, daily ADK/TTS quotas | Terraform explicitly sets `NEUROMESH_SEED_DEMO=true`. No Cloud Storage archive or scheduler. Cloud CLI now needs reauthentication for fresh inspection. Provisioning or deployment requires a separate reviewed proposal and user approval. |
| Tests/docs | Vitest, Pytest, Playwright, real homepage screenshot, runbooks, research protocol | Only a small backend suite. No migration, scholarly schema, citation-edge, memory, experiment, or report tests yet. |

## Production data audit

- `services/api/neuromesh_api/demo.py` creates 144 synthetic nodes and hundreds of synthetic edges at startup by default; the Cloud Run Terraform environment enables this. Labels identify them as samples, but graph metrics and visual prominence can still mislead.
- `apps/web/src/demo.ts` supplies synthetic graph counts while the API is unavailable. This can falsely look like a populated system before the fetch completes or after failure.
- `apps/web/src/App.tsx` renders an illustrative, hardcoded research trend and static coordinates. The trend is labeled as a visual sample but is inappropriate on a production research dashboard.
- `GraphScene.tsx` adds 2,200 ambient particles. Those have no entity IDs and are visual background; they must stay visually and semantically separate from scientific records.
- `Research` excludes demo nodes, and analytics defaults to `demo=0`; these parts are already more careful. Existing OpenAlex/GitHub/Hugging Face/NIH rows in the local database originate from the public APIs, but the ingestion schema does not yet preserve enough scholarly lineage.
- The current assistant reports record matches and source URLs; it explicitly avoids causal claims. It has no memory or ability to substantiate a multi-hop citation relationship.

## Prioritized implementation checklist

### Gate 1 — application foundation

- [x] Stop automatic demo seeding and exclude pre-existing demo rows from production graph/status/retrieval. Show an honest empty or offline state.
- [x] Remove the hardcoded trend and coordinates from the production Observatory; show measured values or an unavailable state.
- [x] Preserve and verify the existing 3D head, audio interruption, graph interactions, and all current pages.
- [x] Add explicit API failure and last verified response timestamps; test startup and error paths.

Gate 1 validation: local API returned 32 public source records, 32 visible entities, and zero fabricated relationships; the previous demo rows remained stored but were not returned. Pytest: 5 passed, 1 PostgreSQL test skipped because an isolated test URL is not configured. Vitest: 5 passed. Playwright against the updated local API: 9 passed, including offline empty state and speech-driven face/interruption. The current local screenshot shows only source-backed graph nodes. Cloud Run has not been updated.

### Gate 2 — real scholarly data

- [x] Verify current OpenAlex API behavior and account limits. Enrich a bounded OpenAlex connector with identifiers, authorships, institutions, topics, references, and license/access fields.
- [x] Add schema migration and validated, idempotent scholarly persistence; record job failures without overwriting the last verified snapshot.
- [x] Run a live OpenAlex ingestion into a local database and inspect source IDs, raw metadata, timestamps, and provenance.
- [x] Add arXiv and PubMed connectors after the OpenAlex path passes; follow their current API policies.

Gate 2 validation: bounded live local syncs returned five normalized records per source. Current local database: 47 public source records in total, including 15 scholarly records from this pilot. The NCBI developer contact was passed from local Git configuration only. Connector and provenance tests pass. This is a bounded local sample, not production-scale ingestion; scheduled jobs and broad coverage remain open.

### Gate 3 — real graph and assistant

- [x] Materialize only source-backed paper, author, institution, topic, and citation edges with evidence and confidence class.
- [ ] Add graph expansion and source/date/topic filters, evidence inspection, and actual citation-path highlighting. Evidence inspection and explicit SSE edge highlighting work; Research now filters source, year, topic, and institution, while graph expansion remains.
- [x] Make local and ADK answers cite retrieved records, disclose uncertainty, and persist session context for operator sessions.

Gate 3 validation: the local API returns 180 source-backed entities and 165 evidence-linked current relationships. A Playwright integration followed a real OpenAlex paper through Research, graph evidence inspection, camera focus/reset, and a cited assistant answer. Camera focus now uses the node's live simulated position; the evidence inspector scrolls without covering graph controls. Cross-source identity resolution and historical graph navigation remain open, so Gate 3 is partial.

### Gate 4 — cognitive research and experiments

- [x] Implement operator episodic, evidence-linked semantic, and temporal relationship withdrawal with provenance. Conflict policy experiments remain.
- [ ] Freeze real-data evaluation sets and run matched A/B/C/D configurations under the same model and budget. Fifteen attribution tasks have been drafted from real records but await manual review; no provider run has occurred.
- [ ] Persist trials, confidence intervals, latency/tokens/cost, ablations, and failure states; export CSV/JSON and evidence-linked Markdown reports. Schema, runner, exports, and report generation pass isolated tests; real measured runs and ablations remain.

### Gate 5 — full validation and deployment proposal

- [ ] Run backend, frontend, browser, ingestion, graph, memory, experiment, security and load checks.
- [ ] Review incremental cloud resource needs and monthly charges with the user before any Cloud Run deployment or new paid resource.
- [ ] Review repository contents and history for secrets before requesting authorization to push.

No gate is marked complete merely because a UI element exists. Each gate requires passing tests and observed end-to-end behavior.

## Post-audit deployment verification — 2026-11-16

After the audit, release 0.3.0 was deployed to the existing Cloud Run service by an in-place Terraform update (0 added, 1 changed, 0 destroyed). Cloud SQL remained `RUNNABLE`. A bounded deployed sync stored five new scholarly records each from OpenAlex, arXiv, and PubMed. The public API reported 47 source records, 15 normalized scholarly works, 171 visible source-backed entities, and 159 evidenced relationships. One public cited investigation selected relationship IDs present in the graph; one operator ADK investigation and a Cloud TTS WAV request passed. A deployed Chrome voice turn observed 20 nonzero PCM animation frames and successful interruption. Eleven Playwright tests passed against the public URL. The homepage image in the README was recaptured from that deployed release.

These checks validate a working research browsing and assistant path. They do not complete the cognitive benchmark, scheduled ingestion, cross-source resolution, or physical microphone test. The two 15-task local evaluation drafts remain unreviewed and were not copied into Cloud SQL. No GitHub push was made.

## Access-control update — 2026-11-17

Release 0.3.1 changes the public interface to read-only. The backend rejects unauthenticated investigations before writing an investigation record or calling an agent, and existing synchronization and speech routes remain token-protected. The Admin button verifies the private token against `/api/admin/session` before exposing chat, voice, and sync controls. Admin questions default to indexed evidence; Google ADK requires a separate Gemini switch. Signing out stops active work and clears the tab's conversation. Local API and browser tests cover guest denial, invalid sign-in, authorized research, voice behavior, and sign-out. The release deployed as one Cloud Run image update with no new resources; 13 Playwright tests and an operator/guest API check passed against the live URL. The README screenshot was recaptured from that deployed revision.
