/**
 * Suggestion engine — context-aware ranking, slash hints, and chains.
 *
 * Pure functions extracted from InputBar for testability.
 */

export const BASE_SUGGESTIONS = [
  'Summarize this page',
  'Explain this code',
  'What does this do?',
  'Write a function that ',
  'Help me understand ',
  'How do I ',
  'Fix this bug',
  'Refactor this to ',
  'What are the key points?',
  'Compare these approaches',
  'Give me an example of ',
  'Translate this to ',
  'Debug this error',
  'Optimize this code',
  'What is the difference between ',
  '/search ',
  '/web ',
  '/reason ',
  '/new',
  '/help',
];

export const SLASH_COMMANDS = {
  '/search ': { hint: '<query>', description: 'Search DuckDuckGo' },
  '/web ':    { hint: '<url>',   description: 'Fetch a web page' },
  '/reason ': { hint: '<query>', description: 'Step-by-step reasoning' },
  '/new':     { hint: '',        description: 'New conversation' },
  '/help':    { hint: '',        description: 'Show commands' },
};

/**
 * Detect patterns in assistant response content.
 * @param {string} content — assistant message text
 * @returns {{ hasCode: boolean, hasList: boolean, hasError: boolean, hasExplanation: boolean }}
 */
export function detectResponsePatterns(content) {
  if (!content) return { hasCode: false, hasList: false, hasError: false, hasExplanation: false };
  const c = content.toLowerCase();
  return {
    hasCode: c.includes('```') || c.includes('function') || c.includes('class '),
    hasList: c.includes('1.') || c.includes('- ') || c.includes('* '),
    hasError: c.includes('error') || c.includes('bug') || c.includes('fix') || c.includes('issue'),
    hasExplanation: c.includes('means') || c.includes('because') || c.includes('essentially'),
  };
}

/**
 * Build context-aware follow-up suggestions from last assistant content.
 * @param {string} lastAssistantContent
 * @param {{ url?: string, selection?: string } | null} pageContext
 * @returns {string[]}
 */
export function getContextSuggestions(lastAssistantContent, pageContext = null) {
  if (!lastAssistantContent) return [];

  const { hasCode, hasList, hasError, hasExplanation } = detectResponsePatterns(lastAssistantContent);
  const follow = [];

  if (hasCode) {
    follow.push(
      'Explain this step by step',
      'Can you add error handling?',
      'Write tests for this',
      'Can you optimize this?',
      'Show me a different approach',
    );
  }
  if (hasList) {
    follow.push(
      'Tell me more about the first one',
      'Which do you recommend?',
      'Can you elaborate on that?',
      'Give me a comparison table',
    );
  }
  if (hasError) {
    follow.push(
      'What caused this error?',
      'How do I prevent this?',
      'Are there other edge cases?',
      'Show me the fix',
    );
  }
  if (hasExplanation) {
    follow.push(
      'Can you give me an example?',
      'Explain it more simply',
      'How does this relate to ',
      'What are the tradeoffs?',
    );
  }

  // Page-context-aware suggestions
  if (pageContext) {
    if (pageContext.url && pageContext.url.includes('github.com')) {
      follow.push('What does this PR do?');
    }
    if (pageContext.selection) {
      follow.push('Explain this selection');
    }
  }

  // General follow-ups always available after a response
  follow.push('Go deeper on that', 'Can you rewrite that?', 'Thanks, now ', 'What about ');

  return follow;
}

/**
 * Get slash command parameter hint for current input.
 * @param {string} input
 * @returns {string} — hint text to show after input, or ''
 */
export function getSlashHint(input) {
  if (!input || !input.startsWith('/')) return '';

  // Exact slash command match — show hint
  for (const [cmd, { hint }] of Object.entries(SLASH_COMMANDS)) {
    if (input === cmd) return hint;
  }

  // Partial slash match — complete command + hint
  const lower = input.toLowerCase();
  for (const [cmd, { hint }] of Object.entries(SLASH_COMMANDS)) {
    if (cmd.startsWith(lower) && cmd !== lower) {
      return cmd.slice(input.length) + hint;
    }
  }

  return '';
}

/**
 * Ranked suggestion matching — context suggestions take priority.
 * @param {string} input
 * @param {string[]} contextSuggestions
 * @param {string[]} baseSuggestions
 * @returns {string} — remaining text of best match, or ''
 */
export function rankSuggestions(input, contextSuggestions, baseSuggestions) {
  if (!input || input.length < 2) return '';

  const lower = input.toLowerCase();

  // Slash input — only match slash commands
  if (input.startsWith('/')) {
    const hint = getSlashHint(input);
    if (hint) return hint;
    return '';
  }

  // Context suggestions first
  for (const s of contextSuggestions) {
    if (s.toLowerCase().startsWith(lower)) {
      return s.slice(input.length);
    }
  }

  // Then base suggestions
  for (const s of baseSuggestions) {
    if (s.toLowerCase().startsWith(lower)) {
      return s.slice(input.length);
    }
  }

  return '';
}

// Static follow-up chains: maps a context suggestion to its next suggestion
const CHAIN_MAP = {
  'Explain this step by step': 'Can you simplify that?',
  'Write tests for this': 'Can you add edge cases?',
  'What caused this error?': 'How do I prevent this in the future?',
  'Show me the fix': 'Are there other places this could happen?',
  'Which do you recommend?': 'What are the tradeoffs?',
  'Can you give me an example?': 'Show me a more advanced example',
  'Go deeper on that': 'Can you summarize the key takeaway?',
  'Can you rewrite that?': 'Explain the changes you made',
};

/**
 * Build a suggestion chain — follow-ups to follow-ups.
 * @param {string} lastContent — last assistant content
 * @param {number} depth — 0 = getContextSuggestions, 1 = chain follow-up
 * @returns {string} — preemptive suggestion, or ''
 */
export function buildSuggestionChain(lastContent, depth = 0) {
  if (!lastContent) return '';

  if (depth === 0) {
    const suggestions = getContextSuggestions(lastContent);
    return suggestions.length > 0 ? suggestions[0] : '';
  }

  if (depth === 1) {
    // Look at what the depth-0 suggestion was and find its chain follow-up
    const suggestions = getContextSuggestions(lastContent);
    if (suggestions.length === 0) return '';
    const primary = suggestions[0];
    return CHAIN_MAP[primary] || '';
  }

  return '';
}
