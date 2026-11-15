import os

from fastapi.testclient import TestClient

from neuromesh_api.main import app
from neuromesh_api.ingestion import normalize_github, persist_records
from neuromesh_api.analytics import analyze_graph
from neuromesh_api.store import reserve_usage


def test_seed_and_api(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
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
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'test.db'))
    with TestClient(app) as client:
        record = normalize_github({'id': 5, 'full_name': 'example/ai-agents',
                                   'html_url': 'https://github.com/example/ai-agents', 'created_at': '2024-01-01'})
        assert persist_records([record], 'ai-agents') == 1
        assert persist_records([record], 'ai-agents') == 1  # idempotent upsert
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


def test_cloud_speech_is_operator_only_and_not_cached(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'test.db'))
    monkeypatch.setenv('NEUROMESH_ADMIN_TOKEN', 'local-test-secret')
    monkeypatch.setenv('NEUROMESH_ENABLE_CLOUD_TTS', 'true')
    monkeypatch.setattr('neuromesh_api.voice.synthesize', lambda text: b'RIFF-test-audio')
    with TestClient(app) as client:
        assert client.post('/api/speech', json={'text': 'Hello'}).status_code == 403
        response = client.post('/api/speech', json={'text': 'Hello'},
                               headers={'X-Admin-Token': 'local-test-secret'})
        assert response.status_code == 200
        assert response.content == b'RIFF-test-audio'
        assert response.headers['cache-control'] == 'no-store'
        monkeypatch.setenv('NEUROMESH_TTS_DAILY_CHAR_LIMIT', '5')
        assert client.post('/api/speech', json={'text': 'again'}, headers={'X-Admin-Token': 'local-test-secret'}).status_code == 429


def test_lexical_clusters_are_reproducible_and_source_backed(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'test.db'))
    with TestClient(app) as client:
        records = [normalize_github({'id': index, 'full_name': title,
                   'html_url': f'https://github.com/{title}', 'created_at':'2024-01-01'})
                   for index,title in [(1,'example/agent-framework'),(2,'sample/agent-framework'),(3,'sample/vision-model')]]
        persist_records(records, 'agent')
        first = client.get('/api/clusters').json()
        assert first == client.get('/api/clusters').json()
        assert first['record_count'] == 3
        assert first['cluster_count'] == 1
        assert all(member['source_url'].startswith('https://github.com/') for member in first['clusters'][0]['members'])
        assert reserve_usage('adk_invocation',1,1)
        assert not reserve_usage('adk_invocation',1,1)
