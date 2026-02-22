import { describe, it, expect } from 'vitest';
import { parseContent, sanitize } from '../src/utils.js';

describe('parseContent', () => {
  it('returns plain text as single text part', () => {
    const parts = parseContent('Hello world');
    expect(parts).toEqual([{ type: 'text', value: 'Hello world' }]);
  });

  it('extracts a single code block', () => {
    const input = 'Before\n```python\nprint("hi")\n```\nAfter';
    const parts = parseContent(input);
    expect(parts).toHaveLength(3);
    expect(parts[0]).toEqual({ type: 'text', value: 'Before\n' });
    expect(parts[1].type).toBe('code');
    expect(parts[1].language).toBe('python');
    expect(parts[1].value).toContain('print("hi")');
    expect(parts[2]).toEqual({ type: 'text', value: '\nAfter' });
  });

  it('extracts multiple code blocks', () => {
    const input = '```js\nconst a = 1;\n```\ntext\n```bash\nls\n```';
    const parts = parseContent(input);
    expect(parts).toHaveLength(3);
    expect(parts[0].type).toBe('code');
    expect(parts[0].language).toBe('js');
    expect(parts[1].type).toBe('text');
    expect(parts[2].type).toBe('code');
    expect(parts[2].language).toBe('bash');
  });

  it('handles empty input', () => {
    const parts = parseContent('');
    expect(parts).toEqual([{ type: 'text', value: '' }]);
  });
});

describe('sanitize', () => {
  it('allows safe tags', () => {
    const html = '<strong>bold</strong> <em>italic</em>';
    const result = sanitize(html);
    expect(result).toBe('<strong>bold</strong> <em>italic</em>');
  });

  it('strips script tags', () => {
    const html = '<script>alert("xss")</script>hello';
    const result = sanitize(html);
    expect(result).toBe('alert("xss")hello');
  });

  it('strips div tags', () => {
    const html = '<div>content</div>';
    const result = sanitize(html);
    expect(result).toBe('content');
  });

  it('strips img tags', () => {
    const html = '<img src="x" onerror="alert(1)">';
    const result = sanitize(html);
    expect(result).toBe('');
  });

  it('preserves href on anchor tags', () => {
    const html = '<a href="https://example.com" onclick="evil()">link</a>';
    const result = sanitize(html);
    expect(result).toBe('<a href="https://example.com" target="_blank" rel="noopener">link</a>');
  });

  it('strips event handlers from non-anchor tags', () => {
    const html = '<strong onmouseover="alert(1)">text</strong>';
    const result = sanitize(html);
    expect(result).toBe('<strong>text</strong>');
  });
});
