from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .demo import seed_demo
from .analytics import analyze_graph
from .ingestion import SOURCES, synchronize
from .ml import cluster_records
from .research import investigate
from .store import connect, graph, initialize, status, reserve_usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    if os.getenv('NEUROMESH_SEED_DEMO', 'true').lower() == 'true':
        with connect() as db:
            seed_demo(db)
    yield


app = FastAPI(title='NeuroMesh AI API', version='0.2.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('NEUROMESH_CORS_ORIGIN', 'http://localhost:5173')],
                   allow_methods=['GET','POST'], allow_headers=['Content-Type','X-Admin-Token'])
_request_times: dict[str, deque[float]] = defaultdict(deque)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


class SyncRequest(BaseModel):
    source: str
    query: str = Field(default='artificial intelligence', min_length=2, max_length=100)
    limit: int = Field(default=12, ge=1, le=30)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def authorized(token: str | None) -> bool:
    required = os.getenv('NEUROMESH_ADMIN_TOKEN')
    return bool(required and token and secrets.compare_digest(required, token))


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


@app.get('/api/clusters')
def get_clusters():
    return cluster_records()


@app.get('/api/agent-executions')
def get_agent_executions(x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT id,agent_name,state,model_id,token_count,started_at,finished_at,error FROM agent_executions ORDER BY started_at DESC LIMIT 30')]


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
    allow_adk = authorized(x_admin_token)
    return StreamingResponse(investigate(request.question, allow_adk=allow_adk), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.post('/api/admin/sync')
async def sync_source(request: SyncRequest, x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Admin token required')
    if request.source not in SOURCES:
        raise HTTPException(status_code=422, detail='Unsupported source')
    try:
        return await synchronize(request.source, request.query, request.limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'{request.source} synchronization failed: {type(exc).__name__}') from exc


@app.post('/api/speech')
def speech(request: SpeechRequest, x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    if os.getenv('NEUROMESH_ENABLE_CLOUD_TTS') != 'true':
        raise HTTPException(status_code=503, detail='Cloud speech is not configured')
    if not reserve_usage('cloud_tts_chars', len(request.text), int(os.getenv('NEUROMESH_TTS_DAILY_CHAR_LIMIT','20000'))):
        raise HTTPException(status_code=429, detail='Daily speech budget exhausted')
    from .voice import synthesize
    try:
        audio = synthesize(request.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Speech synthesis failed: {type(exc).__name__}') from exc
    return Response(content=audio, media_type='audio/wav', headers={'Cache-Control': 'no-store'})


static_dir = os.getenv('NEUROMESH_STATIC_DIR')
if static_dir:
    app.mount('/', StaticFiles(directory=static_dir, html=True), name='web')
