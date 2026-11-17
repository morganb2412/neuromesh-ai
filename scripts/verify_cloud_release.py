"""Check the deployed research path without exposing the operator token."""
import argparse
import json

import httpx

from sync_cloud_scholarly import terraform_output


def read_events(response: httpx.Response) -> list[tuple[str, dict]]:
    response.raise_for_status()
    events = []
    for block in response.text.split('\n\n'):
        lines = block.splitlines()
        name = next((line[7:] for line in lines if line.startswith('event: ')), None)
        data = next((line[6:] for line in lines if line.startswith('data: ')), None)
        if name and data:
            events.append((name, json.loads(data)))
    return events


def verify():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-operator', action='store_true',
                        help='Make one capped ADK request and one Cloud TTS request')
    args = parser.parse_args()
    base = terraform_output('app_url')
    with httpx.Client(timeout=120.0) as client:
        health = client.get(f'{base}/api/health')
        health.raise_for_status()
        assert health.json()['ok'] is True
        status = client.get(f'{base}/api/status')
        status.raise_for_status()
        status = status.json()
        graph_response = client.get(f'{base}/api/graph')
        graph_response.raise_for_status()
        graph = graph_response.json()
        assert status['counts']['scholarly_records'] >= 15
        assert status['counts']['entities'] == len(graph['nodes'])
        assert status['counts']['relationships'] == len(graph['edges'])
        assert all(edge['evidence_id'] in graph['evidence'] for edge in graph['edges'])
        assert all(any(source['source'] == name and source['records'] >= 5
                       for source in status['sources']) for name in ('openalex', 'arxiv', 'pubmed'))
        paper = next(node for node in graph['nodes'] if node['kind'] == 'PAPER' and
                     node['source'] == 'openalex' and any(edge['source_id'] == node['id'] and
                     edge['kind'] == 'AUTHORED_BY' for edge in graph['edges']))
        question = f'Who authored {paper["label"]}?'
        events = read_events(client.post(f'{base}/api/investigate', json={'question': question}))
        completed = next(payload for name, payload in events if name == 'investigation.completed')
        path = next(payload for name, payload in events if name == 'graph.path.selected')
        assert paper['source_record_id'] in [item['url'] for item in completed['citations']]
        assert set(path['relationship_ids']) <= {edge['id'] for edge in graph['edges']}
        result = {'url': base, 'records': status['counts']['source_records'],
                  'scholarly_records': status['counts']['scholarly_records'],
                  'entities': len(graph['nodes']), 'relationships': len(graph['edges']),
                  'cited_answer': True, 'evidence_path': True}
        if args.with_operator:
            token = terraform_output('operator_token')
            headers = {'X-Admin-Token': token}
            lab = client.get(f'{base}/api/laboratory', headers=headers)
            lab.raise_for_status()
            assert 'datasets' in lab.json()
            agent_events = read_events(client.post(f'{base}/api/investigate',
                                                    json={'question': question}, headers=headers))
            errors = [payload for name, payload in agent_events if name == 'agent.error']
            assert not errors, f'ADK failed: {errors}'
            assert any(name == 'agent.activated' and payload.get('mode') == 'adk'
                       for name, payload in agent_events)
            speech = client.post(f'{base}/api/speech', json={'text': 'NeuroMesh research is ready.'},
                                 headers=headers)
            speech.raise_for_status()
            assert speech.content.startswith(b'RIFF')
            result.update({'operator_adk': True, 'speech_wav_bytes': len(speech.content)})
        print(json.dumps(result))


if __name__ == '__main__':
    verify()
