# NeuroMesh Cognitive Research Laboratory proposal

**Question.** Can structured episodic and semantic memory improve knowledge retention, continual updating, and evidence-grounded reasoning in an AI research agent?

**Unit of evaluation.** A frozen, human-reviewed task derived from attributable public scientific records. The same base model and task budget will be used in each configuration.

**Interventions.** A: no persistent memory. B: sparse/vector retrieval. C: graph retrieval. D: hybrid retrieval with episodic, semantic, and temporal policies. Each mechanism will be ablated separately before a claim about its contribution.

**Outcomes.** Exact and reviewer-graded answer accuracy, citation support, abstention, update correctness, multi-hop path validity, latency, token use, and execution cost. Paired trials and confidence intervals will be reported with failures included.

**Current status.** Real-data ingestion and a first-author attribution pilot are implemented locally. The latest frozen-corpus draft has 15 unreviewed tasks and no paid model runs. An earlier draft remains pending as a prior version. These are infrastructure checks, not evidence for the central hypothesis.
