"""Deterministic TF-IDF document clustering over indexed public record titles.

This is a lexical baseline, not a semantic or causal finding. Every member retains
its source URL, and the input fingerprint makes reruns auditable.
"""
import hashlib
import math
import re
from collections import Counter

from .store import connect

STOP = {'the','and','for','with','from','using','into','that','this','are','its','via','based'}


def cluster_records(threshold: float = 0.35):
    with connect() as db:
        records = [dict(row) for row in db.execute(
            'SELECT id,source,title,source_url FROM source_records ORDER BY id LIMIT 500')]
    fingerprint = hashlib.sha256('\n'.join(f"{r['id']}|{r['title']}" for r in records).encode()).hexdigest()
    tokens = [Counter(t for t in re.findall(r'[a-z0-9]{3,}', r['title'].casefold()) if t not in STOP) for r in records]
    document_frequency = Counter(t for doc in tokens for t in doc)
    n = len(records)
    vectors = []
    for doc in tokens:
        weights = {t: (1 + math.log(count)) * (math.log((n+1)/(document_frequency[t]+1))+1) for t,count in doc.items()}
        norm = math.sqrt(sum(v*v for v in weights.values())) or 1
        vectors.append({t:v/norm for t,v in weights.items()})
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i+1,n):
            if not vectors[i] or not vectors[j]:
                continue
            smaller,larger = sorted((vectors[i],vectors[j]),key=len)
            similarity = sum(weight * larger.get(term,0) for term,weight in smaller.items())
            if similarity >= threshold:
                parent[root(j)] = root(i)
    groups = {}
    for i,record in enumerate(records):
        groups.setdefault(root(i),[]).append(record)
    clusters = [group for group in groups.values() if len(group)>1]
    clusters.sort(key=lambda group:(-len(group),group[0]['id']))
    return {'method':'TF-IDF cosine similarity, connected components at threshold 0.35',
            'dataset_sha256':fingerprint,'record_count':n,'threshold':threshold,
            'cluster_count':len(clusters),'singleton_count':n-sum(map(len,clusters)),
            'clusters':[{'size':len(group),'members':group} for group in clusters[:20]],
            'limitation':'Title similarity reflects lexical overlap only; it does not establish scientific or funding relationships.'}
