import os

import pytest

from neuromesh_api.analytics import analyze_graph
from neuromesh_api.ingestion import normalize_github, normalize_openalex, persist_records
from neuromesh_api.store import connect, graph, initialize, status


@pytest.mark.skipif(not os.getenv('NEUROMESH_TEST_POSTGRES_URL'), reason='isolated PostgreSQL URL not configured')
def test_postgres_schema_ingestion_and_metrics(monkeypatch):
    monkeypatch.setenv('NEUROMESH_DATABASE_URL', os.environ['NEUROMESH_TEST_POSTGRES_URL'])
    initialize()
    record = normalize_github({'id': 991172, 'full_name': 'neuromesh-test/agent-evidence',
                               'html_url': 'https://github.com/neuromesh-test/agent-evidence',
                               'created_at': '2025-01-01'})
    assert persist_records([record], 'agent-evidence') == 1
    assert persist_records([record], 'agent-evidence') == 1
    live = graph()
    assert any(n['label'] == record['title'] and not n['demo'] for n in live['nodes'])
    assert live['edges'] == []  # repository search results alone establish no research relationship
    assert status()['counts']['source_records'] >= 1
    first = analyze_graph()
    assert first == analyze_graph()
    scholarly = normalize_openalex({
        'id': 'https://openalex.org/W991172', 'display_name': 'PostgreSQL Provenance Check',
        'publication_date': '2025-04-01', 'authorships': [{
            'author': {'id': 'https://openalex.org/A991172', 'display_name': 'Test Author'},
            'institutions': []}], 'topics': [], 'referenced_works': [],
    })
    assert persist_records([scholarly], 'provenance') == 1
    after = graph()
    assert any(edge['kind'] == 'AUTHORED_BY' for edge in after['edges'])
    with connect() as db:
        assert db.execute('SELECT COUNT(*) AS n FROM source_record_versions WHERE source_record_id=?',
                          (scholarly['id'],)).fetchone()['n'] == 1
        assert db.execute("SELECT COUNT(*) AS n FROM semantic_assertions WHERE status='current'").fetchone()['n'] >= 1
