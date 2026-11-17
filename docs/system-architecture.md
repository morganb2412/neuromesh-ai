# System architecture

NeuroMesh keeps the existing React/Three.js Observatory and FastAPI service. The browser receives source-backed graph data through `/api/graph` and investigation steps through Server-Sent Events. The 3D face uses the same investigation and audio state as the chat; its jaw follows playback amplitude or browser speech boundaries. It does not display model internals.

```text
OpenAlex / arXiv / PubMed  →  bounded connector  →  versioned raw record
                                             ↓
                                  normalized scholarly row
                                             ↓
                           evidence + typed graph relationships
                                             ↓
                          semantic assertions and retrieval catalog
                                             ↓
React Observatory ← graph JSON + SSE ← FastAPI research/ADK boundary
```

SQLite is the local store; Cloud SQL PostgreSQL is supported by the existing SQL adapter. Schema migrations add scholarly lineage, episodic/semantic memory, and experiment records. The local database and raw API responses are ignored by Git. Repeated ingestion upserts the source record, retains a distinct raw version by SHA-256, and withdraws relationships no longer present in the latest source metadata. Source observations and past versions remain queryable.

The public interface exposes read-only records, graph evidence, and analytics. Research questions require Admin sign-in with the operator token. Admin questions default to deterministic retrieval and citations; an explicit Gemini switch allows bounded Google ADK research and verification calls. Cloud TTS also requires the token and an explicit voice action. Experimental model calls have no HTTP execution route and require an explicit approval flag in the Python runner. The laboratory API is read-only and operator-only.

## Trust boundaries

- Connectors call fixed public API hosts. Retrieved titles, abstracts, and metadata are untrusted data; they cannot become tool instructions.
- Deterministic parsers normalize identifiers and create relationships only from source fields. Model prose is not persisted as a verified relationship.
- Browser code receives no provider key. The operator token stays in browser memory and is sent only to protected endpoints.
- A public visitor can inspect evidence and browse records. They cannot submit investigations, run ingestion, use speech, call ADK, or run experiments.
- Release 0.3.1 is deployed on the existing Cloud Run service and Cloud SQL database. Terraform added no resource during this release. Further resource or cost changes require review.

## Current limits

The local graph is still small. Author and institution identity resolution across sources is intentionally conservative. Evaluation retrieval uses sparse title features; it does not yet benchmark dense embeddings or a full cognitive-memory curriculum. Graph expansion, historical visual snapshots, scheduled ingestion, and multi-user authentication remain open work.
