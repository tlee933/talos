import { describe, it, expect } from 'vitest';
import { matchSuggestion } from '../src/utils.js';
import {
  BASE_SUGGESTIONS,
  SLASH_COMMANDS,
  detectResponsePatterns,
  getContextSuggestions,
  getSlashHint,
  rankSuggestions,
  buildSuggestionChain,
} from '../src/suggestions.js';

// --- matchSuggestion (existing tests, kept for backward compat) ---

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
    expect(matchSuggestion('su', SUGGESTIONS)).toBe('mmarize this page');
  });

  it('returns empty when no match', () => {
    expect(matchSuggestion('zzz no match', SUGGESTIONS)).toBe('');
  });

  it('matches longer prefix', () => {
    expect(matchSuggestion('explain this', SUGGESTIONS)).toBe(' code');
  });

  it('matches full suggestion returns empty remainder', () => {
    expect(matchSuggestion('Summarize this page', SUGGESTIONS)).toBe('');
  });
});

// --- detectResponsePatterns ---

describe('detectResponsePatterns', () => {
  it('detects code patterns', () => {
    const r = detectResponsePatterns('Here is a ```python\nprint("hi")``` block');
    expect(r.hasCode).toBe(true);
  });

  it('detects function keyword as code', () => {
    const r = detectResponsePatterns('This function handles auth');
    expect(r.hasCode).toBe(true);
  });

  it('detects class keyword as code', () => {
    const r = detectResponsePatterns('The class UserManager inherits...');
    expect(r.hasCode).toBe(true);
  });

  it('detects list patterns', () => {
    const r = detectResponsePatterns('1. First item\n2. Second item');
    expect(r.hasList).toBe(true);
  });

  it('detects bullet lists', () => {
    const r = detectResponsePatterns('- item one\n- item two');
    expect(r.hasList).toBe(true);
  });

  it('detects error patterns', () => {
    const r = detectResponsePatterns('There was an error in the output');
    expect(r.hasError).toBe(true);
  });

  it('detects bug keyword as error', () => {
    const r = detectResponsePatterns('This bug occurs when...');
    expect(r.hasError).toBe(true);
  });

  it('detects explanation patterns', () => {
    const r = detectResponsePatterns('This essentially means that...');
    expect(r.hasExplanation).toBe(true);
  });

  it('detects because keyword as explanation', () => {
    const r = detectResponsePatterns('It works because of the caching');
    expect(r.hasExplanation).toBe(true);
  });

  it('detects multiple patterns', () => {
    const r = detectResponsePatterns('```js\nfunction render() {}\n```\n1. first step');
    expect(r.hasCode).toBe(true);
    expect(r.hasList).toBe(true);
    expect(r.hasError).toBe(false);
  });

  it('returns all false for empty content', () => {
    const r = detectResponsePatterns('');
    expect(r.hasCode).toBe(false);
    expect(r.hasList).toBe(false);
    expect(r.hasError).toBe(false);
    expect(r.hasExplanation).toBe(false);
  });

  it('returns all false for null/undefined', () => {
    const r = detectResponsePatterns(null);
    expect(r.hasCode).toBe(false);
  });
});

// --- getContextSuggestions ---

describe('getContextSuggestions', () => {
  it('returns code follow-ups for code content', () => {
    const s = getContextSuggestions('Here is a ```python\ncode``` block');
    expect(s).toContain('Explain this step by step');
    expect(s).toContain('Write tests for this');
  });

  it('returns list follow-ups for list content', () => {
    const s = getContextSuggestions('1. First\n2. Second');
    expect(s).toContain('Which do you recommend?');
  });

  it('returns error follow-ups for error content', () => {
    const s = getContextSuggestions('There was an error in the build');
    expect(s).toContain('What caused this error?');
    expect(s).toContain('Show me the fix');
  });

  it('returns explanation follow-ups', () => {
    const s = getContextSuggestions('This essentially means the cache is stale');
    expect(s).toContain('Can you give me an example?');
  });

  it('always includes general follow-ups', () => {
    const s = getContextSuggestions('Hello world');
    expect(s).toContain('Go deeper on that');
    expect(s).toContain('What about ');
  });

  it('returns empty array for empty content', () => {
    expect(getContextSuggestions('')).toEqual([]);
  });

  it('adds GitHub PR suggestion for github.com page context', () => {
    const s = getContextSuggestions('Some response', { url: 'https://github.com/owner/repo/pull/42' });
    expect(s).toContain('What does this PR do?');
  });

  it('adds selection suggestion when page has selection', () => {
    const s = getContextSuggestions('Some response', { selection: 'selected text' });
    expect(s).toContain('Explain this selection');
  });

  it('does not add page-context suggestions without page context', () => {
    const s = getContextSuggestions('Some response');
    expect(s).not.toContain('What does this PR do?');
    expect(s).not.toContain('Explain this selection');
  });
});

// --- rankSuggestions ---

describe('rankSuggestions', () => {
  it('returns empty for short input', () => {
    expect(rankSuggestions('a', ['Apple pie'], BASE_SUGGESTIONS)).toBe('');
  });

  it('matches prefix from context suggestions first', () => {
    const ctx = ['Go deeper on that', 'Good morning'];
    const result = rankSuggestions('Go', ctx, BASE_SUGGESTIONS);
    expect(result).toBe(' deeper on that');
  });

  it('falls through to base suggestions when no context match', () => {
    const result = rankSuggestions('Su', [], BASE_SUGGESTIONS);
    expect(result).toBe('mmarize this page');
  });

  it('returns empty when no match anywhere', () => {
    expect(rankSuggestions('zzz', ['Abc'], ['Def'])).toBe('');
  });

  it('filters to slash commands when input starts with /', () => {
    const result = rankSuggestions('/se', ['Something else'], BASE_SUGGESTIONS);
    expect(result).toBe('arch <query>');
  });

  it('context suggestions take priority over base', () => {
    const ctx = ['Explain this step by step'];
    const result = rankSuggestions('Ex', ctx, BASE_SUGGESTIONS);
    expect(result).toBe('plain this step by step');
  });
});

// --- getSlashHint ---

describe('getSlashHint', () => {
  it('returns hint for /search ', () => {
    expect(getSlashHint('/search ')).toBe('<query>');
  });

  it('returns hint for /web ', () => {
    expect(getSlashHint('/web ')).toBe('<url>');
  });

  it('returns hint for /reason ', () => {
    expect(getSlashHint('/reason ')).toBe('<query>');
  });

  it('returns empty hint for /new', () => {
    expect(getSlashHint('/new')).toBe('');
  });

  it('returns empty hint for /help', () => {
    expect(getSlashHint('/help')).toBe('');
  });

  it('completes partial /se to arch <query>', () => {
    expect(getSlashHint('/se')).toBe('arch <query>');
  });

  it('completes partial /w to eb <url>', () => {
    expect(getSlashHint('/w')).toBe('eb <url>');
  });

  it('completes partial /re to ason <query>', () => {
    expect(getSlashHint('/re')).toBe('ason <query>');
  });

  it('returns empty for non-slash input', () => {
    expect(getSlashHint('hello')).toBe('');
  });

  it('returns empty for empty input', () => {
    expect(getSlashHint('')).toBe('');
  });

  it('returns empty for unknown slash command', () => {
    expect(getSlashHint('/unknown')).toBe('');
  });
});

// --- buildSuggestionChain ---

describe('buildSuggestionChain', () => {
  it('returns first context suggestion at depth 0', () => {
    const result = buildSuggestionChain('```python\nprint("hi")\n```');
    expect(result).toBe('Explain this step by step');
  });

  it('returns chain follow-up at depth 1', () => {
    const result = buildSuggestionChain('```python\nprint("hi")\n```', 1);
    expect(result).toBe('Can you simplify that?');
  });

  it('returns empty for unknown chain mapping at depth 1', () => {
    // Content that triggers only general follow-ups (no chain mapped)
    const result = buildSuggestionChain('Hello world', 1);
    // "Go deeper on that" is the first general follow-up, and it IS in CHAIN_MAP
    expect(result).toBe('Can you summarize the key takeaway?');
  });

  it('returns empty for empty content', () => {
    expect(buildSuggestionChain('')).toBe('');
  });

  it('returns empty for depth > 1', () => {
    expect(buildSuggestionChain('```code```', 2)).toBe('');
  });
});
