# Cognitive research methodology

## Question

Can structured episodic and semantic memory improve agent retention, continual updates, and evidence-grounded reasoning compared with conventional retrieval? This is a testable hypothesis, not a project finding. It is distinct from the earlier 2023–2026 study of public investment and adoption, which has not been run.

## Implemented pilot

The current laboratory can draft first-author attribution tasks from real normalized scholarly records. Every task starts `pending_review`. A human must inspect the original URL and expected author before marking it validated. Dataset content and the current source/semantic corpus are fingerprinted with SHA-256; a changed corpus blocks a run against the old version. Experiments register a question, hypothesis, prompt version, and dataset version. Four configurations use one model and the same tasks and repeat count: A has no retrieval; B uses sparse title retrieval; C adds current evidence-linked graph paths; D adds episodic context when a session is supplied. The pilot runner currently passes no episode session, so D does not test episodic retention yet. Do not interpret D as a complete cognitive-memory result.

The runner records each response, parse state, exact normalized answer score, citation attribution, latency, token counts, model ID, and error. Price is recorded only if explicit provider price variables are configured. It computes a seeded percentile bootstrap interval over task trials. Small or overlapping trials are not evidence of superiority. No real provider evaluation has been authorized or run; the local test uses an isolated fake provider only.

## Required next protocol

Freeze a manually reviewed set with multi-hop, temporal correction, retention, abstention, and conflicting-evidence tasks. Separate train/retrieval material from evaluation questions; document the base model and its likely pretraining overlap. Use identical source access, task order, model settings, token ceiling, repeat count, and cost ceiling. Register ablations for episodic memory, semantic graph, and temporal withdrawal separately. Compare paired task outcomes with uncertainty intervals and report missing runs, provider errors, and latency/cost distributions. A negative result is acceptable. Do not infer biological plausibility or causal improvement from this pilot.
