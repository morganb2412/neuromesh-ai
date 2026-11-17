"""External research memory with explicit provenance and temporal withdrawal.

No operation here changes model weights or treats an AI-generated statement as a
source fact. Episodic records are operator-only; semantic assertions are copied
deterministically from evidenced graph relationships.
"""
import json
import uuid
from datetime import datetime, timezone

from .store import connect

POLICY_VERSION = 1


def consolidate_relations(db, source_record_ids: list[str]) -> int:
    """Copy evidenced, source-backed relationships into temporal semantic memory."""
    if not source_record_ids:
        return 0
    placeholders = ','.join('?' for _ in source_record_ids)
    rows = db.execute(f'''SELECT r.id,r.source_id,r.target_id,r.kind,r.confidence,r.evidence_id,
        v.source_record_id,o.withdrawn_at FROM relationships r
        JOIN evidence v ON v.id=r.evidence_id
        JOIN entities a ON a.id=r.source_id JOIN entities b ON b.id=r.target_id
        LEFT JOIN relationship_observations o ON o.relationship_id=r.id
        WHERE v.source_record_id IN ({placeholders}) AND r.demo=0
        AND r.confidence IN ('verified','extracted')
        AND a.source_record_id IS NOT NULL AND b.source_record_id IS NOT NULL''', source_record_ids)
    count = 0
    for row in rows:
        withdrawn = row['withdrawn_at']
        db.execute('''INSERT INTO semantic_assertions(id,relationship_id,subject_id,predicate,object_id,
            evidence_id,source_record_id,confidence,policy_version,status,valid_to)
            VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,valid_to=excluded.valid_to''',
            (f'memory:{row["id"]}', row['id'], row['source_id'], row['kind'], row['target_id'],
             row['evidence_id'], row['source_record_id'], row['confidence'], POLICY_VERSION,
             'superseded' if withdrawn else 'current', withdrawn))
        count += 1
    return count


def record_episode(session_id: str, investigation_id: str, event_type: str,
                   content: dict, source_record_id: str | None = None) -> str:
    episode_id = str(uuid.uuid4())
    with connect() as db:
        db.execute('''INSERT INTO memory_episodes(id,session_id,investigation_id,event_type,
            content_json,source_record_id,occurred_at) VALUES(?,?,?,?,?,?,?)''',
            (episode_id, session_id, investigation_id, event_type,
             json.dumps(content, separators=(',', ':')), source_record_id,
             datetime.now(timezone.utc).isoformat(timespec='microseconds')))
    return episode_id


def session_context(session_id: str, limit: int = 6) -> list[dict]:
    with connect() as db:
        rows = db.execute('''SELECT id,event_type,content_json,source_record_id,occurred_at
            FROM memory_episodes WHERE session_id=? ORDER BY occurred_at DESC,id DESC LIMIT ?''',
            (session_id, limit))
        return [{key: value for key, value in dict(row).items() if key != 'content_json'} |
                {'content': json.loads(row['content_json'])} for row in rows]


def semantic_neighbors(entity_id: str, limit: int = 30) -> list[dict]:
    with connect() as db:
        return [dict(row) for row in db.execute('''SELECT m.id,m.subject_id,m.predicate,m.object_id,
            m.confidence,m.source_record_id,m.observed_at,v.url,v.excerpt
            FROM semantic_assertions m JOIN evidence v ON v.id=m.evidence_id
            WHERE m.status='current' AND (m.subject_id=? OR m.object_id=?)
            ORDER BY m.observed_at DESC,m.id LIMIT ?''', (entity_id, entity_id, limit))]
