"""Local, zero-provider-cost dataset preparation and review.

Run with `.venv/bin/python scripts/research_lab.py ...` from the repository root.
This command never calls a model or creates a paid cloud resource.
"""
import argparse
import json

from neuromesh_api.experiments import (create_experiment, draft_attribution_dataset,
                                       laboratory_state, review_task)
from neuromesh_api.store import connect, initialize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    draft = commands.add_parser('draft', help='Draft pending tasks from source-backed scholarly records')
    draft.add_argument('--name', required=True)
    draft.add_argument('--limit', type=int, default=20)
    commands.add_parser('list', help='List datasets, experiment definitions, and recorded runs')
    tasks = commands.add_parser('tasks', help='Inspect every task and its source URL before human review')
    tasks.add_argument('dataset_id')
    review = commands.add_parser('review', help='Record an explicit human task decision')
    review.add_argument('task_id')
    review.add_argument('decision', choices=('validated', 'rejected'))
    register = commands.add_parser('register', help='Register a hypothesis against a frozen dataset')
    register.add_argument('dataset_id')
    register.add_argument('--question', required=True)
    register.add_argument('--hypothesis', required=True)
    args = parser.parse_args()
    initialize()
    if args.command == 'draft':
        result = draft_attribution_dataset(args.name, args.limit)
    elif args.command == 'list':
        result = laboratory_state()
    elif args.command == 'tasks':
        with connect() as db:
            result = [dict(row) for row in db.execute('''SELECT id,question,expected_json,citations_json,
                source_record_ids_json,review_state FROM evaluation_tasks WHERE dataset_id=? ORDER BY id''',
                (args.dataset_id,))]
    elif args.command == 'review':
        review_task(args.task_id, args.decision)
        result = {'task_id': args.task_id, 'decision': args.decision}
    else:
        result = {'experiment_id': create_experiment(args.dataset_id, args.question, args.hypothesis)}
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
