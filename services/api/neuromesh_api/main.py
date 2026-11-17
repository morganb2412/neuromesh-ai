from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analytics import analyze_graph
from .ingestion import SOURCES, synchronize
from .ml import cluster_records
from .research import investigate
from .memory import semantic_neighbors, session_context
from .experiments import laboratory_state, export_run, markdown_report
from .store import connect, graph, initialize, status, reserve_usage


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield


app = FastAPI(title='NeuroMesh AI API', version='0.3.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('NEUROMESH_CORS_ORIGIN', 'http://localhost:5173')],
                   allow_methods=['GET','POST'], allow_headers=['Content-Type','X-Admin-Token'])
_request_times: dict[str, deque[float]] = defaultdict(deque)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    session_id: UUID | None = None


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
def get_analytics():
    return analyze_graph()


@app.get('/api/clusters')
def get_clusters():
    return cluster_records()


@app.get('/api/agent-executions')
def get_agent_executions(x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT id,agent_name,state,model_id,token_count,started_at,finished_at,error FROM agent_executions ORDER BY started_at DESC LIMIT 30')]


@app.get('/api/memory/session/{session_id}')
def get_memory_session(session_id: UUID, x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    return session_context(str(session_id))


@app.get('/api/memory/semantic/{entity_id}')
def get_semantic_memory(entity_id: str):
    if len(entity_id) > 160:
        raise HTTPException(status_code=422, detail='Entity ID too long')
    return semantic_neighbors(entity_id)


@app.get('/api/laboratory')
def get_laboratory(x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    return laboratory_state()


@app.get('/api/experiments/runs/{run_id}/export')
def get_run_export(run_id: UUID, format: str = 'json', x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    if format not in ('csv', 'json'):
        raise HTTPException(status_code=422, detail='Use csv or json')
    try:
        content = export_run(str(run_id), format)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=content, media_type='text/csv' if format == 'csv' else 'application/json',
                    headers={'Content-Disposition': f'attachment; filename="neuromesh-{run_id}.{format}"'})


@app.get('/api/experiments/runs/{run_id}/report')
def get_run_report(run_id: UUID, x_admin_token: str | None = Header(default=None)):
    if not authorized(x_admin_token):
        raise HTTPException(status_code=403, detail='Operator token required')
    try:
        content = markdown_report(str(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(content=content, media_type='text/markdown',
                    headers={'Content-Disposition': f'attachment; filename="neuromesh-{run_id}.md"'})


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
    return StreamingResponse(investigate(request.question, allow_adk=allow_adk,
                                         session_id=str(request.session_id) if request.session_id else None), media_type='text/event-stream',
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
