# Deployment cost gate

No GCP resources were provisioned. For a small prototype in `us-central1`, two request billed Cloud Run services with zero minimum instances may stay within the published free tier at low traffic; this is a scenario, not a guarantee. A continuously running Cloud SQL `db-f1-micro` starts at about **$7.67 per 730-hour month** for compute alone (`$0.0105 × 730`), before storage, backups, egress, logging, and any Gemini, speech, or embedding calls. A practical personal budget should reserve **$15–$50/month** for a minimal persistent installation and set billing alerts at $10 and $25. Provider calls need separate hard quotas and an operator approval gate. Recalculate with the Google Cloud calculator before enabling billing or deploying.

Sources: [Cloud Run pricing](https://cloud.google.com/run/pricing), [Cloud SQL pricing](https://cloud.google.com/sql/pricing), [Cloud Storage pricing](https://cloud.google.com/storage/pricing).
