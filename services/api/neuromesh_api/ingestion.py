"""Explicit, bounded public API connectors with provenance-preserving normalization."""
import hashlib
import json
from urllib.parse import quote

import httpx

from .store import connect

HEADERS = {'User-Agent': 'NeuroMeshAI/0.1 (public research prototype)', 'Accept': 'application/json'}
SOURCES = ('openalex', 'github', 'huggingface', 'nih')


async def fetch_source(source: str, query: str = 'artificial intelligence', limit: int = 12):
    if source not in SOURCES or not 1 <= limit <= 30 or len(query) > 100:
        raise ValueError('Invalid source, query, or limit')
    timeout = httpx.Timeout(12.0)
    async with httpx.AsyncClient(timeout=timeout, headers=HEADERS, follow_redirects=False) as client:
        if source == 'openalex':
            response = await client.get('https://api.openalex.org/works', params={'search': query, 'per-page': limit, 'select': 'id,display_name,publication_date,doi,primary_location'})
            response.raise_for_status()
            return [normalize_openalex(x) for x in response.json().get('results', [])]
        if source == 'github':
            response = await client.get('https://api.github.com/search/repositories', params={'q': query, 'per_page': limit, 'sort': 'updated'}, headers={**HEADERS, 'X-GitHub-Api-Version': '2022-11-28'})
            response.raise_for_status()
            return [normalize_github(x) for x in response.json().get('items', [])]
        if source == 'huggingface':
            response = await client.get('https://huggingface.co/api/models', params={'search': query, 'limit': limit})
            response.raise_for_status()
            return [normalize_huggingface(x) for x in response.json()]
        response = await client.post('https://api.reporter.nih.gov/v2/projects/search', json={'criteria': {'advanced_text_search': {'operator': 'and', 'search_field': 'projecttitle', 'search_text': query}}, 'offset': 0, 'limit': limit})
        response.raise_for_status()
        return [normalize_nih(x) for x in response.json().get('results', [])]


def normalize_openalex(x):
    return {'id': x['id'], 'source': 'openalex', 'title': x.get('display_name') or 'Untitled work', 'url': x.get('doi') or x['id'], 'date': x.get('publication_date'), 'kind': 'PAPER', 'payload': x}


def normalize_github(x):
    return {'id': f"github:{x['id']}", 'source': 'github', 'title': x['full_name'], 'url': x['html_url'], 'date': x.get('created_at'), 'kind': 'REPOSITORY', 'payload': x}


def normalize_huggingface(x):
    return {'id': f"hf:{x['id']}", 'source': 'huggingface', 'title': x['id'], 'url': 'https://huggingface.co/' + quote(x['id']), 'date': x.get('createdAt'), 'kind': 'MODEL', 'payload': x}


def normalize_nih(x):
    identifier = x.get('appl_id') or x.get('core_project_num')
    return {'id': f'nih:{identifier}', 'source': 'nih', 'title': x.get('project_title') or 'Untitled project', 'url': x.get('project_detail_url') or f'https://reporter.nih.gov/project-details/{identifier}', 'date': str(x.get('fiscal_year') or ''), 'kind': 'GRANT', 'payload': x}


def persist_records(records, query='artificial intelligence'):
    with connect() as db:
        topic_id = 'topic:' + hashlib.sha256(query.casefold().encode()).hexdigest()[:16]
        db.execute('INSERT INTO entities(id,label,kind,description,demo) VALUES(?,?,?,?,0) ON CONFLICT(id) DO NOTHING',
                   (topic_id, query, 'SCIENTIFIC_TOPIC', 'Collection query; links below require literal title evidence.'))
        for item in records:
            raw = json.dumps(item['payload'], separators=(',', ':'))
            db.execute('''INSERT INTO source_records(id,source,source_url,title,published_at,payload_json) VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET source=excluded.source,source_url=excluded.source_url,
                       title=excluded.title,published_at=excluded.published_at,payload_json=excluded.payload_json''',
                       (item['id'], item['source'], item['url'], item['title'], item['date'], raw))
            eid = 'entity:' + hashlib.sha256(item['id'].encode()).hexdigest()[:16]
            db.execute('''INSERT INTO entities(id,label,kind,description,source_record_id,demo) VALUES(?,?,?,?,?,0)
                       ON CONFLICT(id) DO UPDATE SET label=excluded.label,kind=excluded.kind,
                       description=excluded.description,source_record_id=excluded.source_record_id,demo=0''',
                       (eid, item['title'], item['kind'], f"Public {item['source']} record", item['id']))
            evidence_id = 'evidence:' + hashlib.sha256(item['id'].encode()).hexdigest()[:16]
            db.execute('''INSERT INTO evidence(id,source_record_id,excerpt,url) VALUES(?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET source_record_id=excluded.source_record_id,
                       excerpt=excluded.excerpt,url=excluded.url''',
                       (evidence_id, item['id'], item['title'], item['url']))
            if query.casefold() in item['title'].casefold():
                edge_id = 'edge:' + hashlib.sha256((item['id'] + query.casefold()).encode()).hexdigest()[:16]
                db.execute('''INSERT INTO relationships(id,source_id,target_id,kind,confidence,evidence_id,demo) VALUES(?,?,?,?,?,?,0)
                           ON CONFLICT(id) DO UPDATE SET source_id=excluded.source_id,target_id=excluded.target_id,
                           kind=excluded.kind,confidence=excluded.confidence,evidence_id=excluded.evidence_id,demo=0''',
                           (edge_id, eid, topic_id, 'MENTIONS', 'verified', evidence_id))
    return len(records)


async def synchronize(source, query='artificial intelligence', limit=12):
    with connect() as db:
        job = db.execute('INSERT INTO ingestion_jobs(source,state) VALUES(?,?) RETURNING id', (source, 'running')).fetchone()['id']
    try:
        records = await fetch_source(source, query, limit)
        count = persist_records(records, query)
        with connect() as db:
            db.execute("UPDATE ingestion_jobs SET state='completed',records=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (count, job))
        return {'source': source, 'records': count, 'job_id': job}
    except Exception as exc:
        with connect() as db:
            db.execute("UPDATE ingestion_jobs SET state='failed',error=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (type(exc).__name__, job))
        raise
