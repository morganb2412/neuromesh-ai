from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS source_records (
 id TEXT PRIMARY KEY, source TEXT NOT NULL, source_url TEXT NOT NULL,
 title TEXT NOT NULL, published_at TEXT, payload_json TEXT NOT NULL,
 retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS entities (
 id TEXT PRIMARY KEY, label TEXT NOT NULL, kind TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '', source_record_id TEXT,
 demo INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
CREATE TABLE IF NOT EXISTS relationships (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL, target_id TEXT NOT NULL,
 kind TEXT NOT NULL, confidence TEXT NOT NULL CHECK(confidence IN ('verified','extracted','inferred','similarity')),
 evidence_id TEXT, demo INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(source_id) REFERENCES entities(id), FOREIGN KEY(target_id) REFERENCES entities(id),
 FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);
CREATE TABLE IF NOT EXISTS evidence (
 id TEXT PRIMARY KEY, source_record_id TEXT NOT NULL, excerpt TEXT NOT NULL,
 url TEXT NOT NULL, FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
CREATE TABLE IF NOT EXISTS ingestion_jobs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, state TEXT NOT NULL,
 records INTEGER NOT NULL DEFAULT 0, error TEXT, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT
);
CREATE TABLE IF NOT EXISTS investigations (
 id TEXT PRIMARY KEY, question TEXT NOT NULL, answer TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_entities_label ON entities(label);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
"""


def db_path() -> Path:
    return Path(os.getenv('NEUROMESH_DB', str(Path(__file__).resolve().parents[3] / 'data' / 'neuromesh.db')))


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    finally:
        db.close()


def initialize():
    with connect() as db:
        db.executescript(SCHEMA)


def graph():
    with connect() as db:
        nodes = [dict(row) for row in db.execute('SELECT id,label,kind,description,demo,source_record_id FROM entities')]
        edges = [dict(row) for row in db.execute('SELECT id,source_id,target_id,kind,confidence,evidence_id,demo FROM relationships')]
        evidence = {row['id']: dict(row) for row in db.execute('SELECT id,source_record_id,excerpt,url FROM evidence')}
    return {'nodes': nodes, 'edges': edges, 'evidence': evidence, 'mode': 'live' if any(not n['demo'] for n in nodes) else 'demo'}


def status():
    with connect() as db:
        counts = {name: db.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0] for name in ('entities','relationships','source_records','evidence')}
        jobs = [dict(r) for r in db.execute('SELECT * FROM ingestion_jobs ORDER BY id DESC LIMIT 12')]
        sources = [dict(r) for r in db.execute('SELECT source,COUNT(*) AS records,MAX(retrieved_at) AS last_sync FROM source_records GROUP BY source')]
    return {'counts': counts, 'jobs': jobs, 'sources': sources, 'configured_adk': bool(os.getenv('NEUROMESH_ENABLE_ADK') == 'true' and os.getenv('NEUROMESH_MODEL')), 'mode': 'live' if counts['source_records'] else 'demo'}
