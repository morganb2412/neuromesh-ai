import { describe, expect, it } from 'vitest';
import { selectMasculineVoice } from '../src/browserVoice';

describe('browser voice selection',()=>{
  it('prefers an available masculine US voice over the default',()=>{
    const voices=[{name:'Samantha',lang:'en-US'},{name:'Eddy (English (United States))',lang:'en-US'},{name:'Daniel',lang:'en-GB'}];
    expect(selectMasculineVoice(voices)?.name).toContain('Eddy');
  });
  it('uses another known masculine voice when Eddy is unavailable',()=>{
    expect(selectMasculineVoice([{name:'Samantha',lang:'en-US'},{name:'Daniel',lang:'en-GB'}])?.name).toBe('Daniel');
  });
});
