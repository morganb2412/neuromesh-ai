"""Controlled, recorded research experiments. No model call is made by default."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import time
import uuid
from collections import Counter
from typing import Protocol

from .memory import session_context
from .store import connect, reserve_usage

CONFIGURATIONS = ('A_base', 'B_vector', 'C_graph', 'D_hybrid')
PROMPT_VERSION = 'research-eval-v1'


class ModelProvider(Protocol):
    model_id: str

    def generate(self, prompt: str) -> dict: ...


class VertexProvider:
    def __init__(self, model_id: str):
        if not os.getenv('GOOGLE_CLOUD_PROJECT') or not model_id:
            raise RuntimeError('Vertex project and verified model ID are required')
        self.model_id = model_id

    def generate(self, prompt: str) -> dict:
        from google import genai
        from google.genai import types

        started = time.monotonic()
        client = genai.Client(vertexai=True, project=os.environ['GOOGLE_CLOUD_PROJECT'],
                              location=os.getenv('GOOGLE_CLOUD_LOCATION', 'global'))
        response = client.models.generate_content(
            model=self.model_id, contents=prompt,
            config=types.GenerateContentConfig(temperature=0, max_output_tokens=512,
                                               response_mime_type='application/json'))
        usage = response.usage_metadata
        return {'text': response.text or '', 'latency_ms': round((time.monotonic() - started) * 1000),
                'tokens_in': int(getattr(usage, 'prompt_token_count', 0) or 0),
                'tokens_out': int(getattr(usage, 'candidates_token_count', 0) or 0)}


def _fingerprint(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _corpus_fingerprint(db) -> str:
    records = [(row['id'], hashlib.sha256(row['payload_json'].encode()).hexdigest())
               for row in db.execute('''SELECT s.id,s.payload_json FROM source_records s
                   JOIN scholarly_records sch ON sch.source_record_id=s.id
                   WHERE sch.validation_status='valid' ORDER BY s.id''')]
    assertions = [(row['relationship_id'], row['status'], row['evidence_id'])
                  for row in db.execute('''SELECT relationship_id,status,evidence_id
                      FROM semantic_assertions ORDER BY relationship_id''')]
    return _fingerprint({'records': records, 'assertions': assertions})


def draft_attribution_dataset(name: str, limit: int = 20) -> dict:
    """Freeze real metadata tasks; each remains pending until human source review."""
    if not 1 <= limit <= 100:
        raise ValueError('Dataset limit must be 1–100')
    with connect() as db:
        corpus_fingerprint = _corpus_fingerprint(db)
        rows = [dict(row) for row in db.execute('''SELECT s.id,s.title,s.source_url,sch.authors_json
            FROM source_records s JOIN scholarly_records sch ON sch.source_record_id=s.id
            WHERE sch.validation_status='valid' ORDER BY s.id LIMIT ?''', (limit,))]
        tasks = []
        for row in rows:
            authors = json.loads(row['authors_json'])
            if not authors:
                continue
            tasks.append({'source_record_ids': [row['id']],
                          'question': f'According to the source record, who is the first listed author of “{row["title"]}”?',
                          'expected': {'answer': authors[0]['name'], 'type': 'first_author',
                                       'corpus_fingerprint': corpus_fingerprint},
                          'citations': [row['source_url']]})
        if not tasks:
            raise ValueError('No author-bearing validated scholarly records are indexed')
        fingerprint = _fingerprint(tasks)
        existing = db.execute('SELECT id,state,task_count FROM evaluation_datasets WHERE fingerprint=?',
                              (fingerprint,)).fetchone()
        if existing:
            return {'id': existing['id'], 'fingerprint': fingerprint,
                    'state': existing['state'], 'task_count': existing['task_count']}
        dataset_id = str(uuid.uuid4())
        db.execute('INSERT INTO evaluation_datasets(id,name,fingerprint,state,task_count) VALUES(?,?,?,?,?)',
                   (dataset_id, name, fingerprint, 'pending_review', len(tasks)))
        for task in tasks:
            db.execute('''INSERT INTO evaluation_tasks(id,dataset_id,question,expected_json,citations_json,
                source_record_ids_json,review_state) VALUES(?,?,?,?,?,?,?)''',
                (str(uuid.uuid4()), dataset_id, task['question'], json.dumps(task['expected']),
                 json.dumps(task['citations']), json.dumps(task['source_record_ids']), 'pending'))
    return {'id': dataset_id, 'fingerprint': fingerprint, 'state': 'pending_review', 'task_count': len(tasks)}


def review_task(task_id: str, decision: str) -> None:
    if decision not in ('validated', 'rejected'):
        raise ValueError('Review decision must be validated or rejected')
    with connect() as db:
        row = db.execute('SELECT dataset_id FROM evaluation_tasks WHERE id=?', (task_id,)).fetchone()
        if not row:
            raise ValueError('Unknown task')
        db.execute('UPDATE evaluation_tasks SET review_state=? WHERE id=?', (decision, task_id))
        counts = [dict(item) for item in db.execute('SELECT review_state,COUNT(*) AS n FROM evaluation_tasks WHERE dataset_id=? GROUP BY review_state',
                                                   (row['dataset_id'],))]
        state = 'validated' if len(counts) == 1 and counts[0]['review_state'] == 'validated' else 'pending_review'
        if any(item['review_state'] == 'rejected' for item in counts):
            state = 'rejected'
        db.execute('UPDATE evaluation_datasets SET state=? WHERE id=?', (state, row['dataset_id']))


def create_experiment(dataset_id: str, question: str, hypothesis: str) -> str:
    with connect() as db:
        dataset = db.execute('SELECT fingerprint FROM evaluation_datasets WHERE id=?', (dataset_id,)).fetchone()
        if not dataset:
            raise ValueError('Unknown dataset')
        experiment_id = str(uuid.uuid4())
        method = {'configurations': list(CONFIGURATIONS), 'prompt_version': PROMPT_VERSION,
                  'dataset_id': dataset_id, 'score': 'exact normalized answer + allowed source URL'}
        db.execute('INSERT INTO experiment_defs(id,question,hypothesis,dataset_version,method_json) VALUES(?,?,?,?,?)',
                   (experiment_id, question, hypothesis, dataset['fingerprint'], json.dumps(method)))
    return experiment_id


def laboratory_state() -> dict:
    """Read-only inventory. A missing run remains missing, never a demo result."""
    with connect() as db:
        datasets = [dict(row) for row in db.execute('''SELECT id,name,fingerprint,state,task_count,created_at
            FROM evaluation_datasets ORDER BY created_at DESC,id DESC LIMIT 30''')]
        experiments = [dict(row) for row in db.execute('''SELECT id,question,hypothesis,dataset_version,method_json,created_at
            FROM experiment_defs ORDER BY created_at DESC,id DESC LIMIT 30''')]
        runs = [dict(row) for row in db.execute('''SELECT id,experiment_id,configuration_json,result_json,state,started_at,finished_at
            FROM experiment_runs ORDER BY started_at DESC,id DESC LIMIT 30''')]
    for item in experiments:
        item['method'] = json.loads(item.pop('method_json'))
    for item in runs:
        item['configuration'] = json.loads(item.pop('configuration_json'))
        item['result'] = json.loads(item.pop('result_json')) if item['result_json'] else None
    return {'datasets': datasets, 'experiments': experiments, 'runs': runs,
            'configurations': list(CONFIGURATIONS)}


def _tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r'[a-z0-9]{3,}', text.casefold()))


def _vector_records(question: str, limit: int = 5) -> list[dict]:
    """Deterministic sparse TF-IDF vector baseline over source titles."""
    with connect() as db:
        records = [dict(row) for row in db.execute('''SELECT s.id,s.title,s.source_url,s.published_at,
            sch.authors_json FROM source_records s JOIN scholarly_records sch ON sch.source_record_id=s.id
            WHERE sch.validation_status='valid' ORDER BY s.id LIMIT 500''')]
    terms = [_tokens(record['title']) for record in records]
    query = _tokens(question)
    df = Counter(term for doc in terms for term in doc)
    n = len(records)
    weights = {term: math.log((n + 1) / (df[term] + 1)) + 1 for term in query}
    scored = []
    for record, doc in zip(records, terms):
        score = sum(query[t] * doc[t] * weights[t] ** 2 for t in query if t in doc)
        if score > 0:
            scored.append((score, record))
    return [record for _, record in sorted(scored, key=lambda item: (-item[0], item[1]['id']))[:limit]]


def retrieve_context(question: str, configuration: str, session_id: str | None = None) -> dict:
    if configuration not in CONFIGURATIONS:
        raise ValueError('Unknown experiment configuration')
    if configuration == 'A_base':
        return {'records': [], 'paths': [], 'episodes': [], 'method': 'No persistent memory or retrieval'}
    records = _vector_records(question)
    paths = []
    if configuration in ('C_graph', 'D_hybrid'):
        with connect() as db:
            for record in records:
                paper = db.execute('SELECT id FROM entities WHERE source_record_id=? AND kind=?',
                                   (record['id'], 'PAPER')).fetchone()
                if paper:
                    paths.extend([dict(row) for row in db.execute('''SELECT m.predicate,t.label AS target,v.url
                        FROM semantic_assertions m JOIN entities t ON t.id=m.object_id
                        JOIN evidence v ON v.id=m.evidence_id
                        WHERE m.subject_id=? AND m.status='current' ORDER BY m.predicate,t.id LIMIT 12''',
                        (paper['id'],))])
    episodes = session_context(session_id, 4) if configuration == 'D_hybrid' and session_id else []
    return {'records': records, 'paths': paths, 'episodes': episodes,
            'method': {'B_vector': 'Sparse TF-IDF title vector',
                       'C_graph': 'Graph path retrieval from title-matched works',
                       'D_hybrid': 'Sparse vector + current graph + operator episodes'}[configuration]}


def _prompt(task: dict, context: dict) -> str:
    records = [{'title': row['title'], 'url': row['source_url'], 'published_at': row['published_at'],
                'authors': [author['name'] for author in json.loads(row['authors_json'])]}
               for row in context['records']]
    return (f'Protocol {PROMPT_VERSION}. Answer the question below. Respond as JSON with keys "answer" and '
            '"citations" (array of exact source URLs). Use only the provided sources for citations; '
            'if unsure, answer "uncertain" and use an empty citations array.\n'
            f'Question: {task["question"]}\n'
            f'Retrieval method: {context["method"]}\n'
            f'Source records: {json.dumps(records, ensure_ascii=False)}\n'
            f'Graph relationships: {json.dumps(context["paths"], ensure_ascii=False)}\n'
            f'Prior operator episodes (context only, not evidence): {json.dumps(context["episodes"], ensure_ascii=False)}')


def _score(text: str, task: dict, allowed_urls: set[str]) -> tuple[dict, dict]:
    try:
        output = json.loads(text)
        if not isinstance(output, dict) or not isinstance(output.get('answer'), str) or not isinstance(output.get('citations'), list):
            raise ValueError('Response is not the required JSON object')
        citations = output['citations']
        if any(not isinstance(url, str) for url in citations):
            raise ValueError('Citation is not a URL string')
        answer = re.sub(r'\W+', '', output['answer'].casefold())
        expected = re.sub(r'\W+', '', task['expected']['answer'].casefold())
        accuracy = int(bool(expected) and expected in answer)
        attribution = int(bool(citations) and set(citations) <= allowed_urls and
                          set(task['citations']) <= set(citations))
        return output, {'accuracy': accuracy, 'citation_accuracy': attribution,
                        'abstained': int('uncertain' in output['answer'].casefold())}
    except (json.JSONDecodeError, ValueError, TypeError):
        return {'raw': text}, {'accuracy': 0, 'citation_accuracy': 0, 'abstained': 0, 'parse_error': True}


def _bootstrap_interval(values: list[float], seed: int = 314159) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(2000))
    return [round(draws[49], 4), round(draws[1949], 4)]


def run_experiment(experiment_id: str, provider: ModelProvider, *, approved: bool = False,
                   repeats: int = 1, max_tasks: int = 10) -> dict:
    if not approved:
        raise PermissionError('A separately approved paid evaluation is required')
    if not 1 <= repeats <= 3 or not 1 <= max_tasks <= 10:
        raise ValueError('Experiment bounds exceeded')
    with connect() as db:
        definition = db.execute('SELECT * FROM experiment_defs WHERE id=?', (experiment_id,)).fetchone()
        if not definition:
            raise ValueError('Unknown experiment')
        dataset_id = json.loads(definition['method_json'])['dataset_id']
        dataset = db.execute('SELECT * FROM evaluation_datasets WHERE id=?', (dataset_id,)).fetchone()
        if not dataset or dataset['state'] != 'validated' or dataset['fingerprint'] != definition['dataset_version']:
            raise ValueError('Dataset must be frozen and manually validated before a run')
        tasks = [dict(row) for row in db.execute('''SELECT * FROM evaluation_tasks WHERE dataset_id=?
            AND review_state='validated' ORDER BY id LIMIT ?''', (dataset_id, max_tasks))]
        if not tasks:
            raise ValueError('No validated tasks')
        current_corpus = _corpus_fingerprint(db)
        if any(json.loads(task['expected_json']).get('corpus_fingerprint') != current_corpus for task in tasks):
            raise ValueError('Source corpus changed after dataset freeze; draft and review a new version')
        run_id = str(uuid.uuid4())
        configuration = {'model_id': provider.model_id, 'repeats': repeats,
                         'max_tasks': max_tasks, 'prompt_version': PROMPT_VERSION,
                         'configurations': list(CONFIGURATIONS)}
        db.execute('INSERT INTO experiment_runs(id,experiment_id,configuration_json,state) VALUES(?,?,?,?)',
                   (run_id, experiment_id, json.dumps(configuration), 'running'))
    for task in tasks:
        task['expected'] = json.loads(task['expected_json'])
        task['citations'] = json.loads(task['citations_json'])
        for name in CONFIGURATIONS:
            context = retrieve_context(task['question'], name)
            allowed = {record['source_url'] for record in context['records']}
            for repeat in range(repeats):
                if not reserve_usage('experiment_model_call', 1,
                                     int(os.getenv('NEUROMESH_EXPERIMENT_DAILY_CALL_LIMIT', '40'))):
                    raise RuntimeError('Daily experiment model-call limit reached')
                trial_id = str(uuid.uuid4())
                try:
                    result = provider.generate(_prompt(task, context))
                    output, score = _score(result['text'], task, allowed)
                    latency = int(result['latency_ms'])
                    usage = {'tokens_in': int(result.get('tokens_in', 0)),
                             'tokens_out': int(result.get('tokens_out', 0))}
                    price_in = os.getenv('NEUROMESH_INPUT_USD_PER_1M')
                    price_out = os.getenv('NEUROMESH_OUTPUT_USD_PER_1M')
                    estimated_cost = (usage['tokens_in'] * float(price_in) + usage['tokens_out'] * float(price_out)) / 1_000_000 if price_in and price_out else None
                    error = None
                except Exception as exc:
                    output, score, latency, usage, estimated_cost = None, None, None, None, None
                    error = type(exc).__name__
                with connect() as db:
                    db.execute('''INSERT INTO experiment_trials(id,run_id,task_id,configuration,trial_index,
                        model_id,prompt_version,output_json,score_json,latency_ms,usage_json,estimated_cost_usd,error)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (trial_id, run_id, task['id'], name, repeat, provider.model_id, PROMPT_VERSION,
                         json.dumps(output) if output is not None else None,
                         json.dumps(score) if score is not None else None, latency,
                         json.dumps(usage) if usage is not None else None, estimated_cost, error))
    result = summarize_run(run_id)
    with connect() as db:
        db.execute('UPDATE experiment_runs SET state=?,result_json=?,finished_at=CURRENT_TIMESTAMP WHERE id=?',
                   ('completed' if result['successful_trials'] else 'failed', json.dumps(result), run_id))
    return result


def summarize_run(run_id: str) -> dict:
    with connect() as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM experiment_trials WHERE run_id=? ORDER BY configuration,task_id,trial_index',
                                               (run_id,))]
    if not rows:
        raise ValueError('Run has no recorded trials')
    summary = {}
    for name in CONFIGURATIONS:
        trials = [row for row in rows if row['configuration'] == name]
        scores = [json.loads(row['score_json']) for row in trials if row['score_json']]
        accuracy = [float(score['accuracy']) for score in scores]
        citations = [float(score['citation_accuracy']) for score in scores]
        summary[name] = {'trials': len(trials), 'successful': len(scores),
                         'accuracy_mean': round(statistics.mean(accuracy), 4) if accuracy else None,
                         'accuracy_95ci': _bootstrap_interval(accuracy),
                         'citation_accuracy_mean': round(statistics.mean(citations), 4) if citations else None,
                         'latency_ms_median': statistics.median([row['latency_ms'] for row in trials if row['latency_ms'] is not None]) if scores else None}
    return {'run_id': run_id, 'successful_trials': sum(item['successful'] for item in summary.values()),
            'configurations': summary, 'method': 'Per-trial exact answer and allowed citation scoring; seeded percentile bootstrap interval'}


def export_run(run_id: str, format: str = 'json') -> str:
    with connect() as db:
        rows = [dict(row) for row in db.execute('SELECT * FROM experiment_trials WHERE run_id=? ORDER BY configuration,task_id,trial_index',
                                               (run_id,))]
    if not rows:
        raise ValueError('No recorded trials for this run')
    if format == 'json':
        return json.dumps(rows, indent=2, default=str)
    if format == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()
    raise ValueError('Unsupported export format')


def markdown_report(run_id: str) -> str:
    with connect() as db:
        run = db.execute('''SELECT r.*,d.question,d.hypothesis,d.dataset_version,d.method_json
            FROM experiment_runs r JOIN experiment_defs d ON d.id=r.experiment_id WHERE r.id=?''', (run_id,)).fetchone()
    if not run or run['state'] != 'completed':
        raise ValueError('A completed run is required for a report')
    result = json.loads(run['result_json'])
    lines = ['# NeuroMesh research run', '', f'Run ID: `{run_id}`',
             f'Model: `{json.loads(run["configuration_json"])["model_id"]}`',
             f'Dataset SHA-256: `{run["dataset_version"]}`', '',
             '## Research question', '', run['question'], '', '## Hypothesis', '', run['hypothesis'], '',
             '## Method', '', f'Prompt version: `{PROMPT_VERSION}`. Four configurations share the same model, tasks, and repeat count.',
             '', '## Measured results', '', '| Configuration | Trials | Accuracy | 95% bootstrap CI | Citation accuracy |',
             '| --- | ---: | ---: | --- | ---: |']
    for name, item in result['configurations'].items():
        lines.append(f'| {name} | {item["trials"]} | {item["accuracy_mean"]} | {item["accuracy_95ci"]} | {item["citation_accuracy_mean"]} |')
    lines += ['', '## Limitations', '',
              'This run measures exact answers and source URL attribution on the frozen task set. It does not establish general intelligence, biological plausibility, or causal benefit from memory. Compare configurations only within the same task and model budget.',
              '', '## Reproduction', '', f'Export trial rows with `/api/experiments/runs/{run_id}/export?format=json` and verify the dataset fingerprint and prompt version.']
    return '\n'.join(lines) + '\n'
