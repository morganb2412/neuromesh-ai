# Initial research protocol

**Question.** Does growth in AI research activity correspond with growth in public investment, open source implementation, and documented adoption from 2023 through 2026?

**Prespecified hypotheses.** H1: quarterly publication volume on retrieval augmented generation and agents correlates positively with repository creation after a 0–4 quarter lag. H2: public award amounts correlate with later publication counts in the same topic taxonomy. H3: repository counts alone are a weak proxy for deployed adoption.

**Indicators.** Use publication date from OpenAlex, award fiscal year and amount from NIH RePORTER and USAspending, and repository creation and release dates from GitHub. A documented adoption observation requires an official case study, filing, or technical document with a date and URL. Record source coverage by quarter and topic.

**Analysis.** Freeze a dataset manifest and code commit before each run. Aggregate by quarter, report missingness, use bootstrap confidence intervals for correlation and sensitivity analyses for topic definitions and lags. Compare against baseline publication growth across all computer science. Do not infer causality from correlations.

**Current result.** No primary experiment has been executed. The local `GET /api/analytics` endpoint computes reproducible PageRank, density, and connected components on the indexed graph. Those measurements describe indexing structure, not the research hypotheses above.
