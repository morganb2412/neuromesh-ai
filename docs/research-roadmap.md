# Research roadmap

| Gate | Local status | Evidence still needed |
| --- | --- | --- |
| Existing application | Passed locally | Cloud release and physical microphone testing on more devices |
| Real scholarly ingestion | OpenAlex, arXiv, PubMed pilot persisted | Scheduled incremental jobs, larger coverage, provider failure monitoring |
| Source-backed graph | Papers and evidenced author, topic, institution, citation edges visible; Research source/year/topic/institution filters | Cross-source identity resolution, graph expansion and temporal UI |
| Research assistant | Local cited answers, graph SSE paths, operator ADK and voice integration | Larger citation-quality evaluation and cloud release |
| Cognitive memory | Operator episodes and evidenced temporal semantic assertions persisted | Conflict-resolution experiments and bounded retention policy |
| Controlled experiments | Frozen dataset workflow and four-config runner implemented | Human review, cognitive task suite, authorized real model trials and ablations |
| Research reporting | JSON/CSV and Markdown generation from recorded trials | Authentic measured run and methodological review |

No cloud changes or GitHub push are included in this phase. The live service remains on its prior image until a reviewed deployment is authorized.
