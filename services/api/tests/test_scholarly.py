import json

from fastapi.testclient import TestClient

from neuromesh_api.ingestion import normalize_openalex, persist_records
from neuromesh_api.main import app
from neuromesh_api.store import connect


def openalex_work(work_number, title, references=()):
    return {
        'id': f'https://openalex.org/W{work_number}', 'display_name': title,
        'publication_date': '2025-04-10', 'doi': f'https://doi.org/10.5555/test{work_number}',
        'ids': {'pmid': None}, 'type': 'article',
        'authorships': [{'author': {'id': 'https://openalex.org/A123', 'display_name': 'Test Author'},
                         'institutions': [{'id': 'https://openalex.org/I456', 'display_name': 'Test Institute'}]}],
        'topics': [{'id': 'https://openalex.org/T789', 'display_name': 'Memory Research', 'score': 0.9}],
        'referenced_works': [f'https://openalex.org/W{number}' for number in references],
        'best_oa_location': {'license': 'cc-by'}, 'open_access': {'oa_status': 'gold'},
    }


def test_source_backed_scholarly_graph_and_version_history(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'scholarly.db'))
    with TestClient(app) as client:
        second = openalex_work(1002, 'Memory Research Results')
        second['authorships'] = []
        second['topics'] = []
        records = [normalize_openalex(openalex_work(1001, 'Memory Research Methods', [1002])),
                   normalize_openalex(second)]
        assert persist_records(records, 'memory research') == 2
        assert persist_records(records, 'memory research') == 2
        with connect() as db:
            scholarly = db.execute('SELECT * FROM scholarly_records WHERE source_record_id=?',
                                   ('https://openalex.org/W1001',)).fetchone()
            assert scholarly['doi'] == '10.5555/test1001'
            assert scholarly['license'] == 'cc-by'
            assert scholarly['validation_status'] == 'valid'
            assert json.loads(scholarly['authors_json'])[0]['name'] == 'Test Author'
            assert db.execute('SELECT COUNT(*) AS n FROM source_record_versions').fetchone()['n'] == 2
        graph = client.get('/api/graph').json()
        kinds = {edge['kind'] for edge in graph['edges']}
        assert {'AUTHORED_BY','AFFILIATED_WITH','HAS_TOPIC','CITES'} <= kinds
        assert all(edge['evidence_id'] in graph['evidence'] for edge in graph['edges'])
        assert all(graph['evidence'][edge['evidence_id']]['url'].startswith('https://openalex.org/W')
                   for edge in graph['edges'])
        response = client.post('/api/investigate', json={'question': 'Find Memory Research Methods'})
        assert response.status_code == 200
        assert 'relationship.discovered' in response.text
        assert 'https://openalex.org/W1001' in response.text
        assert 'graph.path.selected' in response.text

        changed = openalex_work(1001, 'Memory Research Methods (revised)', [1002])
        changed['authorships'] = []
        changed['topics'] = []
        changed['referenced_works'] = []
        persist_records([normalize_openalex(changed)], 'memory research')
        with connect() as db:
            assert db.execute('SELECT COUNT(*) AS n FROM source_record_versions').fetchone()['n'] == 3
            assert db.execute("SELECT COUNT(*) AS n FROM semantic_assertions WHERE status='superseded'").fetchone()['n'] >= 2
        graph_after = client.get('/api/graph').json()
        assert not any(edge['source_id'] == next(node['id'] for node in graph_after['nodes']
                  if node['label'] == changed['display_name']) for edge in graph_after['edges'])
        assert not any(node['kind'] == 'SCIENTIFIC_TOPIC' and node['label'] == 'Memory Research'
                       for node in graph_after['nodes'])
        assert client.get('/api/status').json()['counts']['entities'] == len(graph_after['nodes'])
        assert client.get('/api/analytics').json()['node_count'] == len(graph_after['nodes'])


def test_openalex_rejects_unsourced_or_untitled_work():
    for payload in ({'id': 'https://openalex.org/W42'},
                    {'id': 'https://example.com/W42', 'display_name': 'Untrusted'},
                    {'id': 'https://openalex.org/W42', 'display_name': ' '}):
        try:
            normalize_openalex(payload)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid scholarly record was accepted')


def test_ingestion_batch_rolls_back_on_bad_record(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'atomic.db'))
    with TestClient(app):
        valid = normalize_openalex(openalex_work(2001, 'Atomic Research'))
        try:
            persist_records([valid, {'id': 'broken'}])
        except KeyError:
            pass
        else:
            raise AssertionError('malformed record was accepted')
        with connect() as db:
            assert db.execute('SELECT COUNT(*) AS n FROM source_records').fetchone()['n'] == 0
