import { describe, expect, it } from 'vitest';
import { fallbackGraph, fallbackStatus } from '../src/demo';
describe('offline initial state',()=>{
  it('contains no fabricated research records or counts',()=>{
    expect(fallbackGraph.mode).toBe('empty');
    expect(fallbackGraph.nodes).toEqual([]);
    expect(fallbackGraph.edges).toEqual([]);
    expect(fallbackStatus.counts.source_records).toBe(0);
  });
});
