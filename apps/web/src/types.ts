export type Entity = { id: string; label: string; kind: string; description: string; demo: number; source_record_id: string | null; source: string; published_at: string | null };
export type Edge = { id: string; source_id: string; target_id: string; kind: string; confidence: string; evidence_id: string | null; demo: number };
export type Evidence = { id: string; source_record_id: string; excerpt: string; url: string };
export type GraphData = { nodes: Entity[]; edges: Edge[]; evidence: Record<string, Evidence>; mode: 'empty' | 'live' };
export type Status = { counts: Record<string, number>; jobs: { id: number; source: string; state: string; records: number; error: string | null; started_at: string }[]; sources: { source: string; records: number; last_sync: string }[]; configured_adk: boolean; configured_tts: boolean; mode: 'empty' | 'live' };
export type AvatarState = 'idle' | 'listening' | 'thinking' | 'retrieving' | 'speaking' | 'interrupted' | 'error';
