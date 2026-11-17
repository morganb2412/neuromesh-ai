import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from neuromesh_api.experiments import (create_experiment, draft_attribution_dataset,
                                       export_run, laboratory_state, markdown_report,
                                       review_task, run_experiment)
from neuromesh_api.ingestion import normalize_openalex, persist_records
from neuromesh_api.main import app
from neuromesh_api.store import connect


class RecordedProvider:
    model_id = 'isolated-test-provider'

    def generate(self, prompt):
        assert 'Source records:' in prompt
        return {'text': json.dumps({'answer': 'Test Author',
                                    'citations': ['https://openalex.org/W901']}),
                'latency_ms': 12, 'tokens_in': 20, 'tokens_out': 8}


def test_dataset_review_cost_gate_trials_and_exports(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUROMESH_DATABASE_URL', raising=False)
    monkeypatch.setenv('NEUROMESH_DB', str(tmp_path / 'lab.db'))
    monkeypatch.setenv('NEUROMESH_ADMIN_TOKEN', 'operator-test-key')
    work = {'id': 'https://openalex.org/W901', 'display_name': 'Continual Memory Study',
            'publication_date': '2025-07-01', 'authorships': [{
                'author': {'id': 'https://openalex.org/A901', 'display_name': 'Test Author'},
                'institutions': []}], 'topics': [], 'referenced_works': []}
    with TestClient(app) as client:
        persist_records([normalize_openalex(work)], 'continual memory')
        dataset = draft_attribution_dataset('reviewed real records', 5)
        assert dataset['state'] == 'pending_review'
        assert draft_attribution_dataset('same records', 5)['id'] == dataset['id']
        experiment_id = create_experiment(dataset['id'], 'Does retrieval improve attribution?',
                                          'Grounded variants improve source attribution.')
        with pytest.raises(PermissionError):
            run_experiment(experiment_id, RecordedProvider())
        with pytest.raises(ValueError, match='manually validated'):
            run_experiment(experiment_id, RecordedProvider(), approved=True)
        with connect() as db:
            task_id = db.execute('SELECT id FROM evaluation_tasks WHERE dataset_id=?',
                                 (dataset['id'],)).fetchone()['id']
        review_task(task_id, 'validated')
        assert laboratory_state()['datasets'][0]['state'] == 'validated'
        result = run_experiment(experiment_id, RecordedProvider(), approved=True)
        assert result['successful_trials'] == 4
        assert result['configurations']['A_base']['citation_accuracy_mean'] == 0
        assert result['configurations']['B_vector']['citation_accuracy_mean'] == 1
        assert result['configurations']['C_graph']['accuracy_95ci'] == [1.0, 1.0]
        assert 'isolated-test-provider' in export_run(result['run_id'])
        rows = list(csv.DictReader(io.StringIO(export_run(result['run_id'], 'csv'))))
        assert len(rows) == 4
        assert 'Does retrieval improve attribution?' in markdown_report(result['run_id'])

        assert client.get('/api/laboratory').status_code == 403
        headers = {'X-Admin-Token': 'operator-test-key'}
        listing = client.get('/api/laboratory', headers=headers)
        assert listing.status_code == 200
        assert len(listing.json()['runs']) == 1
        assert client.get(f'/api/experiments/runs/{result["run_id"]}/export?format=csv',
                          headers=headers).status_code == 200
        assert client.get(f'/api/experiments/runs/{result["run_id"]}/report',
                          headers=headers).status_code == 200
        assert client.get(f'/api/experiments/runs/{result["run_id"]}/export?format=xls',
                          headers=headers).status_code == 422
        changed = dict(work, display_name='Continual Memory Study (corrected)')
        persist_records([normalize_openalex(changed)], 'continual memory')
        with pytest.raises(ValueError, match='corpus changed'):
            run_experiment(experiment_id, RecordedProvider(), approved=True)
