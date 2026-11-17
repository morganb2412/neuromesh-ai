"""Explicit, bounded public API connectors with provenance-preserving normalization."""
import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import date
from urllib.parse import quote

import httpx
from defusedxml import ElementTree as SafeET

from .store import connect

HEADERS = {'User-Agent': 'NeuroMeshAI/0.2 (public research prototype)', 'Accept': 'application/json'}
SOURCES = ('openalex', 'arxiv', 'pubmed', 'github', 'huggingface', 'nih')
LOG = logging.getLogger(__name__)
OPENALEX_FIELDS = 'id,display_name,publication_date,doi,ids,authorships,topics,referenced_works,best_oa_location,open_access,primary_location,type,updated_date'


async def request_with_retry(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    for attempt in range(3):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in (429, 500, 502, 503, 504):
                response.raise_for_status()
                return response
            if attempt == 2:
                response.raise_for_status()
            delay = min(5.0, max(0.5, float(response.headers.get('Retry-After', 0.5 * 2 ** attempt))))
        except (httpx.ConnectError, httpx.ReadTimeout):
            if attempt == 2:
                raise
            delay = 0.5 * 2 ** attempt
        await asyncio.sleep(delay)
    raise RuntimeError('retry limit reached')


async def fetch_source(source: str, query: str = 'artificial intelligence', limit: int = 12):
    if source not in SOURCES or not 1 <= limit <= 30 or len(query) > 100:
        raise ValueError('Invalid source, query, or limit')
    timeout = httpx.Timeout(12.0)
    async with httpx.AsyncClient(timeout=timeout, headers=HEADERS, follow_redirects=False) as client:
        if source == 'openalex':
            params = {'search': query, 'per_page': limit, 'select': OPENALEX_FIELDS}
            if os.getenv('OPENALEX_API_KEY'):
                params['api_key'] = os.environ['OPENALEX_API_KEY']
            response = await request_with_retry(client, 'GET', 'https://api.openalex.org/works', params=params)
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get('results'), list):
                raise ValueError('OpenAlex response has no results array')
            LOG.info('OpenAlex returned %s works; reported query cost USD %s', len(body['results']), body.get('meta', {}).get('cost_usd'))
            return [normalize_openalex(x) for x in body['results']]
        if source == 'arxiv':
            clean_query = re.sub(r'[^\w\s-]', ' ', query).strip()
            response = await request_with_retry(client, 'GET', 'https://export.arxiv.org/api/query',
                params={'search_query': f'all:"{clean_query}"', 'start': 0, 'max_results': limit,
                        'sortBy': 'submittedDate', 'sortOrder': 'descending'})
            return normalize_arxiv_feed(response.content)
        if source == 'pubmed':
            return await fetch_pubmed(client, query, limit)
        if source == 'github':
            response = await request_with_retry(client, 'GET', 'https://api.github.com/search/repositories', params={'q': query, 'per_page': limit, 'sort': 'updated'}, headers={**HEADERS, 'X-GitHub-Api-Version': '2022-11-28'})
            return [normalize_github(x) for x in response.json().get('items', [])]
        if source == 'huggingface':
            response = await request_with_retry(client, 'GET', 'https://huggingface.co/api/models', params={'search': query, 'limit': limit})
            return [normalize_huggingface(x) for x in response.json()]
        response = await request_with_retry(client, 'POST', 'https://api.reporter.nih.gov/v2/projects/search', json={'criteria': {'advanced_text_search': {'operator': 'and', 'search_field': 'projecttitle', 'search_text': query}}, 'offset': 0, 'limit': limit})
        return [normalize_nih(x) for x in response.json().get('results', [])]


def openalex_id(value: object, prefix: str) -> str | None:
    if isinstance(value, str) and re.fullmatch(rf'https://openalex\.org/{prefix}[0-9]+', value):
        return value
    return None


def normalize_openalex(x):
    if not isinstance(x, dict):
        raise ValueError('OpenAlex work is not an object')
    work_id = openalex_id(x.get('id'), 'W')
    title = x.get('display_name')
    published = x.get('publication_date')
    if not work_id or not isinstance(title, str) or not title.strip():
        raise ValueError('OpenAlex work missing stable ID or title')
    if published:
        date.fromisoformat(published)
    raw_doi = x.get('doi')
    doi = raw_doi.lower().replace('https://doi.org/', '').strip() if isinstance(raw_doi, str) else None
    if doi and (not doi.startswith('10.') or '/' not in doi):
        doi = None
    authors = []
    institutions = {}
    for item in x.get('authorships') or []:
        author = item.get('author') or {}
        author_id = openalex_id(author.get('id'), 'A')
        affiliations = []
        for institution in item.get('institutions') or []:
            institution_id = openalex_id(institution.get('id'), 'I')
            if institution_id:
                entry = {'id': institution_id, 'name': institution.get('display_name') or institution_id,
                         'ror': institution.get('ror')}
                institutions[institution_id] = entry
                affiliations.append(institution_id)
        authors.append({'id': author_id, 'name': author.get('display_name') or item.get('raw_author_name') or 'Unresolved author',
                        'orcid': author.get('orcid'), 'position': item.get('author_position'),
                        'institutions': affiliations})
    topics = [{'id': topic_id, 'name': item.get('display_name') or topic_id, 'score': item.get('score')}
              for item in (x.get('topics') or []) if (topic_id := openalex_id(item.get('id'), 'T'))]
    references = [reference for value in (x.get('referenced_works') or []) if (reference := openalex_id(value, 'W'))]
    ids = x.get('ids') or {}
    pmid = ids.get('pmid') if isinstance(ids, dict) else None
    arxiv = ids.get('arxiv') if isinstance(ids, dict) else None
    location = x.get('best_oa_location') or x.get('primary_location') or {}
    access = x.get('open_access') or {}
    return {'id': work_id, 'source': 'openalex', 'title': title.strip(), 'url': work_id,
            'date': published, 'kind': 'PAPER', 'payload': x,
            'scholarly': {'source_identifier': work_id.rsplit('/', 1)[-1], 'doi': doi,
                          'pmid': pmid, 'arxiv_id': arxiv, 'authors': authors,
                          'institutions': list(institutions.values()), 'topics': topics,
                          'references': references, 'license': location.get('license'),
                          'access_status': access.get('oa_status'), 'normalization_version': 1,
                          'validation_status': 'valid'}}


ATOM = '{http://www.w3.org/2005/Atom}'
ARXIV = '{http://arxiv.org/schemas/atom}'


def normalize_arxiv_feed(content: bytes) -> list[dict]:
    if len(content) > 3_000_000:
        raise ValueError('arXiv response exceeds bounded size')
    root = SafeET.fromstring(content)
    if root.tag != ATOM + 'feed':
        raise ValueError('arXiv response is not an Atom feed')
    records = []
    for entry in root.findall(ATOM + 'entry'):
        raw_id = entry.findtext(ATOM + 'id') or ''
        match = re.fullmatch(r'https?://(?:export\.)?arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v[0-9]+)?', raw_id)
        title = ' '.join((entry.findtext(ATOM + 'title') or '').split())
        published = entry.findtext(ATOM + 'published')
        if not match or not title or not published:
            raise ValueError('arXiv entry missing stable ID, title, or date')
        identifier = match.group(1)
        date.fromisoformat(published[:10])
        authors = []
        for author in entry.findall(ATOM + 'author'):
            name = ' '.join((author.findtext(ATOM + 'name') or '').split())
            if name:
                local_id = hashlib.sha256(name.casefold().encode()).hexdigest()[:12]
                authors.append({'id': f'arxiv-byline:{identifier}:{local_id}', 'name': name,
                                'orcid': None, 'position': None, 'institutions': [],
                                'identity_scope': 'source_record'})
        categories = [category.attrib['term'] for category in entry.findall(ATOM + 'category') if category.attrib.get('term')]
        doi_text = entry.findtext(ARXIV + 'doi')
        doi = doi_text.lower().strip() if doi_text and doi_text.startswith('10.') else None
        license_node = entry.find(ARXIV + 'license')
        url = f'https://arxiv.org/abs/{identifier}'
        raw_xml = SafeET.tostring(entry, encoding='unicode')
        records.append({'id': f'arxiv:{identifier}', 'source': 'arxiv', 'title': title,
                        'url': url, 'date': published[:10], 'kind': 'PAPER',
                        'payload': {'raw_xml': raw_xml, 'updated': entry.findtext(ATOM + 'updated'),
                                    'summary': ' '.join((entry.findtext(ATOM + 'summary') or '').split()),
                                    'categories': categories},
                        'scholarly': {'source_identifier': identifier, 'doi': doi, 'pmid': None,
                                      'arxiv_id': identifier, 'authors': authors, 'institutions': [],
                                      'topics': [{'id': f'arxiv-category:{code}', 'name': code, 'score': None}
                                                 for code in categories], 'references': [],
                                      'license': license_node.attrib.get('href') if license_node is not None else None,
                                      'access_status': 'open', 'normalization_version': 1,
                                      'validation_status': 'valid'}})
    return records


async def fetch_pubmed(client: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    contact = os.getenv('NCBI_EMAIL', '')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', contact):
        raise ValueError('NCBI_EMAIL must be configured for PubMed E-utilities')
    common = {'db': 'pubmed', 'tool': 'NeuroMeshAI', 'email': contact}
    response = await request_with_retry(client, 'GET',
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',
        params={**common, 'term': query, 'retmax': limit, 'retmode': 'json'})
    body = response.json()
    identifiers = body.get('esearchresult', {}).get('idlist') if isinstance(body, dict) else None
    if not isinstance(identifiers, list) or any(not re.fullmatch(r'[0-9]+', value) for value in identifiers):
        raise ValueError('PubMed ESearch returned invalid identifiers')
    if not identifiers:
        return []
    await asyncio.sleep(0.4)  # NCBI limits unkeyed E-utilities to three requests per second.
    response = await request_with_retry(client, 'GET',
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi',
        params={**common, 'id': ','.join(identifiers), 'retmode': 'xml'})
    return normalize_pubmed_xml(response.content)


def xml_text(element) -> str:
    return ' '.join(''.join(element.itertext()).split()) if element is not None else ''


def normalize_pubmed_xml(content: bytes) -> list[dict]:
    if len(content) > 5_000_000:
        raise ValueError('PubMed response exceeds bounded size')
    root = SafeET.fromstring(content)
    if root.tag != 'PubmedArticleSet':
        raise ValueError('PubMed EFetch response is not PubmedArticleSet')
    records = []
    for article in root.findall('PubmedArticle'):
        pmid = article.findtext('./MedlineCitation/PMID') or ''
        title = xml_text(article.find('./MedlineCitation/Article/ArticleTitle'))
        if not re.fullmatch(r'[0-9]+', pmid) or not title:
            raise ValueError('PubMed article missing PMID or title')
        article_node = article.find('./MedlineCitation/Article')
        doi = None
        for item in article.findall('./PubmedData/ArticleIdList/ArticleId'):
            if item.attrib.get('IdType') == 'doi' and item.text and item.text.startswith('10.'):
                doi = item.text.lower().strip()
                break
        date_node = article_node.find('ArticleDate') if article_node is not None else None
        if date_node is None:
            date_node = article.find('./MedlineCitation/Article/Journal/JournalIssue/PubDate')
        year = date_node.findtext('Year') if date_node is not None else None
        month = date_node.findtext('Month') if date_node is not None else None
        day = date_node.findtext('Day') if date_node is not None else None
        published = year if year and re.fullmatch(r'[0-9]{4}', year) else None
        if published and month and month.isdigit():
            published += f'-{int(month):02d}'
            if day and day.isdigit():
                published += f'-{int(day):02d}'
        authors = []
        for author in article.findall('./MedlineCitation/Article/AuthorList/Author'):
            name = xml_text(author.find('CollectiveName')) or ' '.join(filter(None, [author.findtext('ForeName'), author.findtext('LastName')]))
            if name:
                local_id = hashlib.sha256(name.casefold().encode()).hexdigest()[:12]
                affiliations = [xml_text(item) for item in author.findall('./AffiliationInfo/Affiliation') if xml_text(item)]
                authors.append({'id': f'pubmed-byline:{pmid}:{local_id}', 'name': name,
                                'orcid': None, 'position': None, 'institutions': [],
                                'affiliations_raw': affiliations, 'identity_scope': 'source_record'})
        topics = []
        for heading in article.findall('./MedlineCitation/MeshHeadingList/MeshHeading'):
            descriptor = heading.find('DescriptorName')
            if descriptor is not None and descriptor.attrib.get('UI'):
                topics.append({'id': f'mesh:{descriptor.attrib["UI"]}', 'name': xml_text(descriptor), 'score': None})
        abstract = ' '.join(xml_text(node) for node in article.findall('./MedlineCitation/Article/Abstract/AbstractText'))
        url = f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'
        records.append({'id': f'pubmed:{pmid}', 'source': 'pubmed', 'title': title,
                        'url': url, 'date': published, 'kind': 'PAPER',
                        'payload': {'raw_xml': SafeET.tostring(article, encoding='unicode'), 'abstract': abstract},
                        'scholarly': {'source_identifier': pmid, 'doi': doi, 'pmid': pmid,
                                      'arxiv_id': None, 'authors': authors, 'institutions': [],
                                      'topics': topics, 'references': [], 'license': None,
                                      'access_status': None, 'normalization_version': 1,
                                      'validation_status': 'valid'}})
    return records


def normalize_github(x):
    return {'id': f"github:{x['id']}", 'source': 'github', 'title': x['full_name'],
            'url': 'https://github.com/' + quote(x['full_name'], safe='/'),
            'date': x.get('created_at'), 'kind': 'REPOSITORY', 'payload': x}


def normalize_huggingface(x):
    return {'id': f"hf:{x['id']}", 'source': 'huggingface', 'title': x['id'], 'url': 'https://huggingface.co/' + quote(x['id']), 'date': x.get('createdAt'), 'kind': 'MODEL', 'payload': x}


def normalize_nih(x):
    identifier = x.get('appl_id') or x.get('core_project_num')
    return {'id': f'nih:{identifier}', 'source': 'nih', 'title': x.get('project_title') or 'Untitled project',
            'url': 'https://reporter.nih.gov/project-details/' + quote(str(identifier), safe=''),
            'date': str(x.get('fiscal_year') or ''), 'kind': 'GRANT', 'payload': x}


def persist_records(records, query='artificial intelligence'):
    from .memory import consolidate_relations
    with connect() as db:
        current_relations: dict[str, set[str]] = {}
        def upsert_entity(identifier, label, kind, record_id, description):
            db.execute('''INSERT INTO entities(id,label,kind,description,source_record_id,demo) VALUES(?,?,?,?,?,0)
                ON CONFLICT(id) DO UPDATE SET label=excluded.label,description=excluded.description''',
                (identifier, label, kind, description, record_id))

        def upsert_relation(source_id, target_id, kind, record, excerpt):
            digest = hashlib.sha256(f'{source_id}|{kind}|{target_id}|{record["id"]}'.encode()).hexdigest()[:24]
            relation_id, evidence_id = f'relation:{digest}', f'relation-evidence:{digest}'
            db.execute('''INSERT INTO evidence(id,source_record_id,excerpt,url) VALUES(?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET excerpt=excluded.excerpt,url=excluded.url''',
                (evidence_id, record['id'], excerpt, record['url']))
            db.execute('''INSERT INTO relationships(id,source_id,target_id,kind,confidence,evidence_id,demo)
                VALUES(?,?,?,?,?,?,0) ON CONFLICT(id) DO UPDATE SET
                confidence=excluded.confidence,evidence_id=excluded.evidence_id,demo=0''',
                (relation_id, source_id, target_id, kind, 'extracted', evidence_id))
            db.execute('''INSERT INTO relationship_observations(relationship_id) VALUES(?)
                ON CONFLICT(relationship_id) DO UPDATE SET last_seen_at=CURRENT_TIMESTAMP,withdrawn_at=NULL''',
                (relation_id,))
            current_relations.setdefault(record['id'], set()).add(relation_id)

        for item in records:
            raw = json.dumps(item['payload'], separators=(',', ':'))
            db.execute('''INSERT INTO source_records(id,source,source_url,title,published_at,payload_json) VALUES(?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET source=excluded.source,source_url=excluded.source_url,
                       title=excluded.title,published_at=excluded.published_at,payload_json=excluded.payload_json,
                       retrieved_at=CURRENT_TIMESTAMP''',
                       (item['id'], item['source'], item['url'], item['title'], item['date'], raw))
            db.execute('''INSERT INTO source_record_versions(source_record_id,payload_sha256,payload_json,source_url)
                VALUES(?,?,?,?) ON CONFLICT(source_record_id,payload_sha256) DO NOTHING''',
                (item['id'], hashlib.sha256(raw.encode()).hexdigest(), raw, item['url']))
            eid = 'entity:' + hashlib.sha256(item['id'].encode()).hexdigest()[:16]
            upsert_entity(eid, item['title'], item['kind'], item['id'], f"Public {item['source']} record")
            evidence_id = 'evidence:' + hashlib.sha256(item['id'].encode()).hexdigest()[:16]
            db.execute('''INSERT INTO evidence(id,source_record_id,excerpt,url) VALUES(?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET source_record_id=excluded.source_record_id,
                       excerpt=excluded.excerpt,url=excluded.url''',
                       (evidence_id, item['id'], item['title'], item['url']))
            scholarly = item.get('scholarly')
            if scholarly:
                db.execute('''INSERT INTO scholarly_records(source_record_id,source_identifier,doi,pmid,arxiv_id,
                    authors_json,institutions_json,topics_json,references_json,license,access_status,
                    normalization_version,validation_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(source_record_id) DO UPDATE SET
                    doi=excluded.doi,pmid=excluded.pmid,arxiv_id=excluded.arxiv_id,
                    authors_json=excluded.authors_json,institutions_json=excluded.institutions_json,
                    topics_json=excluded.topics_json,references_json=excluded.references_json,
                    license=excluded.license,access_status=excluded.access_status,
                    normalization_version=excluded.normalization_version,validation_status=excluded.validation_status,
                    normalized_at=CURRENT_TIMESTAMP''',
                    (item['id'], scholarly['source_identifier'], scholarly['doi'], scholarly['pmid'],
                     scholarly['arxiv_id'], json.dumps(scholarly['authors']), json.dumps(scholarly['institutions']),
                     json.dumps(scholarly['topics']), json.dumps(scholarly['references']), scholarly['license'],
                     scholarly['access_status'], scholarly['normalization_version'], scholarly['validation_status']))
                institutions = {entry['id']: entry for entry in scholarly['institutions']}
                for author in scholarly['authors']:
                    if not author['id']:
                        continue
                    author_id = 'author:' + author['id'].rsplit('/', 1)[-1]
                    scope = 'record-scoped byline' if author.get('identity_scope') == 'source_record' else 'resolved author ID'
                    upsert_entity(author_id, author['name'], 'RESEARCHER', item['id'],
                                  f'{item["source"]} authorship metadata; {scope}')
                    upsert_relation(eid, author_id, 'AUTHORED_BY', item,
                                    f'{item["source"]} byline lists {author["name"]} on this work.')
                    for institution_id in author['institutions']:
                        institution = institutions[institution_id]
                        node_id = 'institution:' + institution_id.rsplit('/', 1)[-1]
                        upsert_entity(node_id, institution['name'], 'ORGANIZATION', item['id'],
                                      f'{item["source"]} authorship affiliation metadata')
                        upsert_relation(author_id, node_id, 'AFFILIATED_WITH', item,
                                        f'{item["source"]} byline lists {institution["name"]} for {author["name"]} on this work.')
                for topic in scholarly['topics']:
                    topic_id = 'topic:' + topic['id'].rsplit('/', 1)[-1]
                    upsert_entity(topic_id, topic['name'], 'SCIENTIFIC_TOPIC', item['id'],
                                  f'{item["source"]} topic or subject classification')
                    upsert_relation(eid, topic_id, 'HAS_TOPIC', item,
                                    f'{item["source"]} metadata classifies this work as {topic["name"]}; classification does not prove its scientific claims.')
        for item in records:
            scholarly = item.get('scholarly')
            if not scholarly:
                continue
            source_id = 'entity:' + hashlib.sha256(item['id'].encode()).hexdigest()[:16]
            for reference in scholarly['references']:
                target_id = 'entity:' + hashlib.sha256(reference.encode()).hexdigest()[:16]
                if db.execute('SELECT 1 FROM entities WHERE id=? AND source_record_id=?', (target_id, reference)).fetchone():
                    upsert_relation(source_id, target_id, 'CITES', item,
                                    f'OpenAlex referenced_works lists {reference} for this work.')
        for item in records:
            old = db.execute('''SELECT r.id FROM relationships r JOIN evidence v ON v.id=r.evidence_id
                WHERE v.source_record_id=? AND r.demo=0 AND r.kind IN
                ('AUTHORED_BY','AFFILIATED_WITH','HAS_TOPIC','CITES')''', (item['id'],))
            for row in old:
                if row['id'] not in current_relations.get(item['id'], set()):
                    db.execute('''INSERT INTO relationship_observations(relationship_id,withdrawn_at)
                        VALUES(?,CURRENT_TIMESTAMP) ON CONFLICT(relationship_id) DO UPDATE SET
                        withdrawn_at=COALESCE(relationship_observations.withdrawn_at,CURRENT_TIMESTAMP)''',
                        (row['id'],))
        consolidate_relations(db, [item['id'] for item in records])
    return len(records)


async def synchronize(source, query='artificial intelligence', limit=12):
    with connect() as db:
        job = db.execute('INSERT INTO ingestion_jobs(source,state) VALUES(?,?) RETURNING id', (source, 'running')).fetchone()['id']
    try:
        records = await fetch_source(source, query, limit)
        count = persist_records(records, query)
        with connect() as db:
            db.execute("UPDATE ingestion_jobs SET state='completed',records=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (count, job))
            db.execute('''INSERT INTO ingestion_checkpoints(source,query,last_success_at) VALUES(?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(source,query) DO UPDATE SET last_success_at=CURRENT_TIMESTAMP''', (source, query))
        return {'source': source, 'records': count, 'job_id': job}
    except Exception as exc:
        with connect() as db:
            db.execute("UPDATE ingestion_jobs SET state='failed',error=?,finished_at=CURRENT_TIMESTAMP WHERE id=?", (type(exc).__name__, job))
            db.execute('INSERT INTO ingestion_failures(id,job_id,source,error) VALUES(?,?,?,?)',
                       (str(uuid.uuid4()), job, source, type(exc).__name__))
        raise
