import { describe, it, expect } from 'vitest';
import { matchSuggestion } from '../src/utils.js';

const SUGGESTIONS = [
  'Summarize this page',
  'Explain this code',
  'What does this do?',
  'Write a function that ',
  'Help me understand ',
];

describe('matchSuggestion', () => {
  it('returns empty for short input', () => {
    expect(matchSuggestion('', SUGGESTIONS)).toBe('');
    expect(matchSuggestion('S', SUGGESTIONS)).toBe('');
  });

  it('matches case-insensitive prefix', () => {
    const result = matchSuggestion('su', SUGGESTIONS);
    expect(result).toBe('mmarize this page');
  });

  it('returns empty when no match', () => {
    const result = matchSuggestion('zzz no match', SUGGESTIONS);
    expect(result).toBe('');
  });

  it('matches longer prefix', () => {
    const result = matchSuggestion('explain this', SUGGESTIONS);
    expect(result).toBe(' code');
  });

  it('matches full suggestion returns empty remainder', () => {
    const result = matchSuggestion('Summarize this page', SUGGESTIONS);
    expect(result).toBe('');
  });
});
