import os

from fastapi.testclient import TestClient

from neuromesh_api.main import app
from neuromesh_api.ingestion import normalize_github, persist_records
from neuromesh_api.analytics import analyze_graph


def test_seed_and_api(tmp_path, monkeypatch):
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'test.db'))
    with TestClient(app) as client:
        assert client.get('/api/health').json() == {'ok': True}
        graph = client.get('/api/graph').json()
        assert graph['mode'] == 'demo'
        assert len(graph['nodes']) == 144
        assert all(n['demo'] for n in graph['nodes'])
        assert client.get('/api/analytics').json()['node_count'] == 0
        assert client.post('/api/admin/sync', json={'source': 'github'}).status_code == 403
        response = client.post('/api/investigate', json={'question': 'What is the funding relationship?'})
        assert response.status_code == 200
        assert 'No matching public records' in response.text
        assert 'investigation.completed' in response.text


def test_provenance_and_deterministic_analytics(tmp_path, monkeypatch):
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'test.db'))
    with TestClient(app) as client:
        record = normalize_github({'id': 5, 'full_name': 'example/ai-agents',
                                   'html_url': 'https://github.com/example/ai-agents', 'created_at': '2024-01-01'})
        assert persist_records([record], 'ai-agents') == 1
        graph = client.get('/api/graph').json()
        live_nodes = [n for n in graph['nodes'] if not n['demo']]
        assert len(live_nodes) == 2
        edge = next(e for e in graph['edges'] if not e['demo'])
        assert edge['confidence'] == 'verified'
        assert graph['evidence'][edge['evidence_id']]['url'] == record['url']
        first = analyze_graph()
        assert first == analyze_graph()
        assert first['node_count'] == 2 and first['edge_count'] == 1
        response = client.post('/api/investigate', json={'question': 'Find ai-agents repository'})
        assert record['url'] in response.text
