# Research roadmap

| Gate | Local status | Evidence still needed |
| --- | --- | --- |
| Existing application | Passed locally and on Cloud Run 0.3.0 | Physical microphone testing on more devices |
| Real scholarly ingestion | OpenAlex, arXiv, PubMed pilot persisted in Cloud SQL | Scheduled incremental jobs, larger coverage, provider failure monitoring |
| Source-backed graph | Cloud graph and evidenced author, topic, institution, citation edges visible; Research source/year/topic/institution filters | Cross-source identity resolution, graph expansion and temporal UI |
| Research assistant | Deployed cited answers, graph SSE paths, operator ADK and Cloud TTS verified | Larger citation-quality evaluation |
| Cognitive memory | Operator episodes and evidenced temporal semantic assertions persisted | Conflict-resolution experiments and bounded retention policy |
| Controlled experiments | Frozen dataset workflow and four-config runner implemented | Human review, cognitive task suite, authorized real model trials and ablations |
| Research reporting | JSON/CSV and Markdown generation from recorded trials | Authentic measured run and methodological review |

The reviewed 0.3.0 deployment updated the existing Cloud Run service in place. No GitHub push was made. Experimental model comparisons still require human task review and separate cost approval.
