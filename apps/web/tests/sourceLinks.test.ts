import { describe, expect, it } from 'vitest';
import { safeSourceUrl } from '../src/sourceLinks';

describe('public source links', () => {
  it('keeps known HTTPS research sources', () => {
    expect(safeSourceUrl('https://arxiv.org/abs/2501.01234')).toBe('https://arxiv.org/abs/2501.01234');
    expect(safeSourceUrl('https://doi.org/10.1234/example')).toBe('https://doi.org/10.1234/example');
    expect(safeSourceUrl('https://github.com/example/project')).toBe('https://github.com/example/project');
  });

  it('rejects executable, deceptive, and non-source links', () => {
    for (const value of ['javascript:alert(1)', 'data:text/html,hello', 'http://github.com/example',
      'https://github.com.evil.example/project', 'https://user:pass@github.com/project']) {
      expect(safeSourceUrl(value)).toBeUndefined();
    }
  });
});
