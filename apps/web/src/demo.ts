import type { GraphData, Status } from './types';

// Start empty. On API failure App retains its last verified response, never a synthetic graph.
export const fallbackGraph: GraphData = { nodes: [], edges: [], evidence: {}, mode: 'empty' };
export const fallbackStatus: Status = {
  counts: { entities: 0, relationships: 0, source_records: 0, evidence: 0, scholarly_records: 0 },
  jobs: [], sources: [], configured_adk: false, configured_tts: false, mode: 'empty',
};
