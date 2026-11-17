# Data provenance

Each source record keeps a source name, source identifier, original URL, title, publication date when supplied, raw payload, and retrieval time. `source_record_versions` retains each distinct observed payload by SHA-256. `scholarly_records` stores normalized DOI, PMID, arXiv ID, authors, institutions, topics, references, access/license fields when available, normalization version, and validation state. Missing source fields remain null or empty; the application does not fill them with generated values.

The first live local pilot retrieved five records each from OpenAlex, arXiv, and PubMed on 2026-11-16. Each record was parsed, stored, and rendered as a source-backed paper. The database also contains older public GitHub, Hugging Face, NIH RePORTER, and OpenAlex records. Local totals are snapshots, not an estimate of the scholarly literature.

Release 0.3.0 repeated the bounded three-source pilot through the deployed operator endpoint into Cloud SQL. The live API returned 15 valid normalized scholarly works and 47 public source records in total. The live graph contained 171 current source-backed entities and 159 evidence-linked relationships. These are deployment verification counts, not a literature census.

Relationships are typed and evidence-linked. `AUTHORED_BY`, `AFFILIATED_WITH`, `HAS_TOPIC`, and `CITES` are formed from provider metadata. `CITES` is only materialized when the referenced work is also indexed. The source record URL and an evidence excerpt back every visible scientific edge. Source-reported authorship and citation metadata are marked `extracted`; their existence in an API response is verified, but their scholarly correctness is not independently audited. Model-inferred edges are never promoted to verified.

On re-ingestion, removed source relationships are withdrawn from the current graph and semantic memory. Previous raw versions and temporal observations are retained. A failed source request records an ingestion failure and does not replace the last verified record. Source timestamps in the UI distinguish last successful retrieval from current connectivity.

API references: [OpenAlex Works](https://help.openalex.org/data/works/attributes/), [arXiv API](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/api/user-manual.md), [NCBI E-utilities](https://www.ncbi.nlm.nih.gov/sites/books/NBK25499/). The NCBI developer contact email is supplied locally through `NCBI_EMAIL`; it is not committed.
