"""Small, ordered schema migrations shared by SQLite and PostgreSQL.

Migrations run after the original tables are initialized. They never rewrite raw
records; version rows preserve each distinct source response for auditability.
"""

MIGRATIONS = [
    (1, 'scholarly_provenance', """
CREATE TABLE IF NOT EXISTS scholarly_records (
 source_record_id TEXT PRIMARY KEY REFERENCES source_records(id),
 source_identifier TEXT NOT NULL, doi TEXT, pmid TEXT, arxiv_id TEXT,
 authors_json TEXT NOT NULL, institutions_json TEXT NOT NULL,
 topics_json TEXT NOT NULL, references_json TEXT NOT NULL,
 license TEXT, access_status TEXT, normalization_version INTEGER NOT NULL,
 validation_status TEXT NOT NULL,
 normalized_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS source_record_versions (
 source_record_id TEXT NOT NULL REFERENCES source_records(id),
 payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
 source_url TEXT NOT NULL, observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(source_record_id,payload_sha256)
);
CREATE TABLE IF NOT EXISTS ingestion_failures (
 id TEXT PRIMARY KEY, job_id INTEGER, source TEXT NOT NULL,
 source_identifier TEXT, error TEXT NOT NULL, payload_json TEXT,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
 source TEXT NOT NULL, query TEXT NOT NULL, cursor TEXT,
 last_success_at TIMESTAMP, PRIMARY KEY(source,query)
);
CREATE INDEX IF NOT EXISTS idx_scholarly_doi ON scholarly_records(doi);
CREATE INDEX IF NOT EXISTS idx_scholarly_pmid ON scholarly_records(pmid);
"""),
    (2, 'cognitive_memory', """
CREATE TABLE IF NOT EXISTS relationship_observations (
 relationship_id TEXT PRIMARY KEY REFERENCES relationships(id),
 first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 withdrawn_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS memory_episodes (
 id TEXT PRIMARY KEY, session_id TEXT NOT NULL, investigation_id TEXT REFERENCES investigations(id),
 event_type TEXT NOT NULL, content_json TEXT NOT NULL, source_record_id TEXT REFERENCES source_records(id),
 occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS semantic_assertions (
 id TEXT PRIMARY KEY, relationship_id TEXT NOT NULL REFERENCES relationships(id),
 subject_id TEXT NOT NULL REFERENCES entities(id), predicate TEXT NOT NULL,
 object_id TEXT NOT NULL REFERENCES entities(id), evidence_id TEXT NOT NULL REFERENCES evidence(id),
 source_record_id TEXT NOT NULL REFERENCES source_records(id), confidence TEXT NOT NULL,
 policy_version INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('current','superseded')),
 observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 valid_from TEXT, valid_to TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_memory_episodes_session ON memory_episodes(session_id,occurred_at);
CREATE INDEX IF NOT EXISTS idx_semantic_assertions_subject ON semantic_assertions(subject_id,status);
"""),
    (3, 'research_experiments', """
CREATE TABLE IF NOT EXISTS experiment_defs (
 id TEXT PRIMARY KEY, question TEXT NOT NULL, hypothesis TEXT NOT NULL,
 dataset_version TEXT NOT NULL, method_json TEXT NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS experiment_runs (
 id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiment_defs(id),
 configuration_json TEXT NOT NULL, result_json TEXT, state TEXT NOT NULL,
 started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS evaluation_datasets (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
 state TEXT NOT NULL CHECK(state IN ('pending_review','validated','rejected')),
 task_count INTEGER NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS evaluation_tasks (
 id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES evaluation_datasets(id),
 question TEXT NOT NULL, expected_json TEXT NOT NULL, citations_json TEXT NOT NULL,
 source_record_ids_json TEXT NOT NULL,
 review_state TEXT NOT NULL CHECK(review_state IN ('pending','validated','rejected')),
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS experiment_trials (
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES experiment_runs(id),
 task_id TEXT NOT NULL REFERENCES evaluation_tasks(id),
 configuration TEXT NOT NULL, trial_index INTEGER NOT NULL,
 model_id TEXT NOT NULL, prompt_version TEXT NOT NULL,
 output_json TEXT, score_json TEXT, latency_ms INTEGER,
 usage_json TEXT, estimated_cost_usd REAL, error TEXT,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(run_id,task_id,configuration,trial_index)
);
CREATE INDEX IF NOT EXISTS idx_experiment_trials_run ON experiment_trials(run_id);
"""),
]


def apply_migrations(db):
    db.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)')
    applied = {row['version'] for row in db.execute('SELECT version FROM schema_migrations')}
    for version, name, sql in MIGRATIONS:
        if version not in applied:
            db.executescript(sql)
            db.execute('INSERT INTO schema_migrations(version,name) VALUES(?,?)', (version, name))
