import { describe, it, expect } from 'vitest';

// Test the autoTitle logic (extracted inline since background.js isn't a module)
function autoTitle(messages) {
  const first = messages.find((m) => m.role === 'user');
  if (!first) return 'Untitled';
  const text = first.content.slice(0, 80).trim();
  return text.length < first.content.length ? text + '...' : text;
}

describe('autoTitle', () => {
  it('extracts title from first user message', () => {
    const messages = [
      { role: 'user', content: 'How do I install Firefox?' },
      { role: 'assistant', content: 'Use dnf.' },
    ];
    expect(autoTitle(messages)).toBe('How do I install Firefox?');
  });

  it('truncates long messages at 80 chars', () => {
    const long = 'x'.repeat(100);
    const messages = [{ role: 'user', content: long }];
    const title = autoTitle(messages);
    expect(title.length).toBeLessThanOrEqual(83); // 80 + "..."
    expect(title).toMatch(/\.\.\.$/);
  });

  it('returns Untitled when no user message', () => {
    const messages = [{ role: 'assistant', content: 'hello' }];
    expect(autoTitle(messages)).toBe('Untitled');
  });

  it('returns Untitled for empty array', () => {
    expect(autoTitle([])).toBe('Untitled');
  });

  it('uses first user message even if not first overall', () => {
    const messages = [
      { role: 'system', content: 'system prompt' },
      { role: 'user', content: 'My question' },
    ];
    expect(autoTitle(messages)).toBe('My question');
  });
});

// Test pruneHistory logic (extracted inline)
function pruneHistory(messages) {
  const totalChars = messages.reduce((sum, m) => sum + (m.content || '').length, 0);
  if (totalChars < 90000 || messages.length <= 7) return messages;
  const first = messages.slice(0, 1);
  const recent = messages.slice(-6);
  return [...first, { role: 'system', content: '[earlier messages pruned]' }, ...recent];
}

describe('pruneHistory', () => {
  it('returns messages unchanged when under threshold', () => {
    const msgs = [
      { role: 'user', content: 'short' },
      { role: 'assistant', content: 'reply' },
    ];
    expect(pruneHistory(msgs)).toEqual(msgs);
  });

  it('prunes when over 90K chars', () => {
    const msgs = Array.from({ length: 20 }, (_, i) => ({
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: 'x'.repeat(5000),
    }));
    const result = pruneHistory(msgs);
    expect(result.length).toBeLessThan(msgs.length);
    expect(result[0]).toEqual(msgs[0]);
    expect(result[result.length - 1]).toEqual(msgs[msgs.length - 1]);
  });

  it('keeps first and last 6 messages', () => {
    const msgs = Array.from({ length: 20 }, (_, i) => ({
      role: 'user',
      content: 'x'.repeat(5000),
    }));
    const result = pruneHistory(msgs);
    expect(result[0].content).toBe(msgs[0].content);
    // Last 6 should match
    for (let i = 0; i < 6; i++) {
      expect(result[result.length - 6 + i].content).toBe(msgs[msgs.length - 6 + i].content);
    }
  });
});
