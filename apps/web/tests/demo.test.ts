import { describe, expect, it } from 'vitest';
import { fallbackGraph } from '../src/demo';
describe('visual seed',()=>{
  it('is explicit demo data with no false provenance',()=>{
    expect(fallbackGraph.mode).toBe('demo');
    expect(fallbackGraph.nodes.length).toBeGreaterThan(100);
    expect(fallbackGraph.nodes.every(n=>n.demo===1 && n.source_record_id===null)).toBe(true);
    expect(fallbackGraph.edges.every(e=>e.demo===1 && e.evidence_id===null)).toBe(true);
  });
});
