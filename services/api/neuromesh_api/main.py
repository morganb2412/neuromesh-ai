from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .demo import seed_demo
from .analytics import analyze_graph
from .ingestion import SOURCES, synchronize
from .research import investigate
from .store import connect, graph, initialize, status


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    with connect() as db:
        seed_demo(db)
    yield


app = FastAPI(title='NeuroMesh AI API', version='0.1.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('NEUROMESH_CORS_ORIGIN', 'http://localhost:5173')],
                   allow_methods=['GET','POST'], allow_headers=['Content-Type','X-Admin-Token'])
_request_times: dict[str, deque[float]] = defaultdict(deque)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


class SyncRequest(BaseModel):
    source: str
    query: str = Field(default='artificial intelligence', min_length=2, max_length=100)
    limit: int = Field(default=12, ge=1, le=30)


@app.get('/api/health')
def health():
    return {'ok': True}


@app.get('/api/graph')
def get_graph():
    return graph()


@app.get('/api/status')
def get_status():
    return status()


@app.get('/api/analytics')
def get_analytics(demo: bool = False):
    return analyze_graph(include_demo=demo)


@app.post('/api/investigate')
async def start_investigation(request: InvestigationRequest, connection: Request, x_admin_token: str | None = Header(default=None)):
    address = connection.client.host if connection.client else 'unknown'
    times = _request_times[address]
    now = time.monotonic()
    while times and now - times[0] > 3600:
        times.popleft()
    if len(times) >= 30:
        raise HTTPException(status_code=429, detail='Hourly investigation limit reached')
    times.append(now)
    required = os.getenv('NEUROMESH_ADMIN_TOKEN')
    allow_adk = bool(required and x_admin_token and secrets.compare_digest(required, x_admin_token))
    return StreamingResponse(investigate(request.question, allow_adk=allow_adk), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.post('/api/admin/sync')
async def sync_source(request: SyncRequest, x_admin_token: str | None = Header(default=None)):
    required = os.getenv('NEUROMESH_ADMIN_TOKEN')
    if not required or not x_admin_token or not secrets.compare_digest(required, x_admin_token):
        raise HTTPException(status_code=403, detail='Admin token required')
    if request.source not in SOURCES:
        raise HTTPException(status_code=422, detail='Unsupported source')
    try:
        return await synchronize(request.source, request.query, request.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'{request.source} synchronization failed: {type(exc).__name__}') from exc
