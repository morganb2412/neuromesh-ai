import type { GraphData, Status } from './types';

export const fallbackGraph: GraphData = (() => {
  const kinds = ['PAPER', 'GRANT', 'MODEL', 'ALGORITHM', 'INDUSTRY', 'REPOSITORY'];
  const topics = ['Retrieval systems', 'Agent systems', 'Foundation models', 'Evaluation', 'Public funding', 'Deployment'];
  const nodes = Array.from({ length: 144 }, (_, i) => ({ id: `demo-${i}`, label: `${topics[i % 6]} / sample ${String(Math.floor(i / 6) + 1).padStart(2, '0')}`, kind: kinds[i % 6], description: 'Seeded visualization sample. This entity has no source record.', demo: 1, source_record_id: null }));
  const edges = nodes.flatMap((n, i) => [1, 2].map(j => ({ id: `demo-edge-${i}-${j}`, source_id: n.id, target_id: nodes[(i + j * 6) % nodes.length].id, kind: 'DEMO_ASSOCIATION', confidence: 'similarity', evidence_id: null, demo: 1 })));
  return { nodes, edges, evidence: {}, mode: 'demo' };
})();
export const fallbackStatus: Status = { counts: { entities: 144, relationships: 288, source_records: 0, evidence: 0 }, jobs: [], sources: [], configured_adk: false, configured_tts: false, mode: 'demo' };
