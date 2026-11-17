"""Bounded operator sync against the existing Cloud Run service.

Reads the existing Terraform operator token privately and never prints it.
This script makes no provider model calls and creates no cloud resources.
"""
import argparse
import json
import subprocess
from pathlib import Path

import httpx

TERRAFORM_DIR = Path(__file__).resolve().parents[1] / 'infrastructure' / 'terraform'
TERRAFORM = Path(__file__).resolve().parents[1] / '.local' / 'bin' / 'terraform'
QUERIES = {
    'openalex': 'continual learning',
    'arxiv': 'continual learning',
    'pubmed': 'continual learning neuroscience',
}


def terraform_output(name: str) -> str:
    result = subprocess.run([str(TERRAFORM), 'output', '-raw', name], cwd=TERRAFORM_DIR,
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error('limit must be between 1 and 10')
    url, token = terraform_output('app_url'), terraform_output('operator_token')
    if not url.startswith('https://') or not token:
        raise SystemExit('Terraform does not expose a deployed HTTPS app and operator token')
    with httpx.Client(timeout=120.0) as client:
        for source, query in QUERIES.items():
            response = client.post(f'{url}/api/admin/sync',
                                   headers={'X-Admin-Token': token},
                                   json={'source': source, 'query': query, 'limit': args.limit})
            if not response.is_success:
                raise SystemExit(f'{source} sync failed: HTTP {response.status_code} '
                                 f'{response.text[:200]}')
            print(json.dumps(response.json()))


if __name__ == '__main__':
    main()
