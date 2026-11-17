"""Bounded local one-shot synchronization; no cloud resources or model calls."""
import argparse
import asyncio
import json
import sys

from neuromesh_api.ingestion import SOURCES, synchronize
from neuromesh_api.store import initialize


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', default='artificial intelligence')
    parser.add_argument('--limit', type=int, default=12)
    parser.add_argument('--source', choices=(*SOURCES, 'all'), default='all')
    args = parser.parse_args()
    initialize()
    failures = 0
    for source in SOURCES if args.source == 'all' else [args.source]:
        try:
            print(json.dumps(await synchronize(source, args.query, args.limit)))
        except Exception as exc:
            failures += 1
            print(json.dumps({'source':source,'error':type(exc).__name__,'detail':str(exc)[:200]}))
    if failures:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
