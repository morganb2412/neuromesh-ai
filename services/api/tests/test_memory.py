from fastapi.testclient import TestClient

from neuromesh_api.ingestion import normalize_openalex, persist_records
from neuromesh_api.main import app
from neuromesh_api.store import connect


def test_operator_episode_context_and_evidence_linked_semantic_memory(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'memory.db'))
    monkeypatch.setenv('NEUROMESH_ADMIN_TOKEN', 'test-operator-secret')
    monkeypatch.delenv('NEUROMESH_ENABLE_ADK', raising=False)
    session_id = '3f90cbb4-1943-4f2c-9486-ac5162293f03'
    payload = {'id': 'https://openalex.org/W1003', 'display_name': 'Evidence Memory Study',
               'publication_date': '2025-01-01', 'authorships': [
                   {'author': {'id': 'https://openalex.org/A1003', 'display_name': 'Research Author'},
                    'institutions': []}], 'topics': [], 'referenced_works': []}
    with TestClient(app) as client:
        persist_records([normalize_openalex(payload)], 'memory')
        graph = client.get('/api/graph').json()
        paper = next(node for node in graph['nodes'] if node['label'] == payload['display_name'])
        semantic = client.get(f'/api/memory/semantic/{paper["id"]}').json()
        assert len(semantic) == 1
        assert semantic[0]['predicate'] == 'AUTHORED_BY'
        assert semantic[0]['url'] == payload['id']

        body = {'question': 'Find Evidence Memory Study', 'session_id': session_id}
        response = client.post('/api/investigate', json=body,
                               headers={'X-Admin-Token': 'test-operator-secret'})
        assert response.status_code == 200
        assert payload['id'] in response.text
        assert client.get(f'/api/memory/session/{session_id}').status_code == 403
        history = client.get(f'/api/memory/session/{session_id}',
                             headers={'X-Admin-Token': 'test-operator-secret'}).json()
        assert [item['event_type'] for item in history] == ['answer', 'question']
        assert history[0]['content']['source_urls'] == [payload['id']]
        with connect() as db:
            assert db.execute("SELECT COUNT(*) AS n FROM semantic_assertions WHERE status='current'").fetchone()['n'] == 1
