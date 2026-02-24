/**
 * Pure utility functions extracted for testability.
 */

const ALLOWED_TAGS = new Set([
  'strong', 'em', 'a', 'code', 'ul', 'ol', 'li', 'p', 'br',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'del',
]);

/**
 * Sanitize HTML — strip tags not in allowlist, keep only href on <a>.
 */
export function sanitize(html) {
  return html.replace(/<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/g, (full, tag) => {
    const lower = tag.toLowerCase();
    const isClosing = full.startsWith('</');

    if (!ALLOWED_TAGS.has(lower)) return '';

    if (isClosing) return `</${lower}>`;

    if (lower === 'a') {
      const hrefMatch = full.match(/href\s*=\s*"([^"]*)"/i) || full.match(/href\s*=\s*'([^']*)'/i);
      if (hrefMatch) {
        return `<a href="${hrefMatch[1]}" target="_blank" rel="noopener">`;
      }
      return '<a>';
    }

    return `<${lower}>`;
  });
}

/**
 * Parse message content into text, code block, and think block parts.
 */
export function parseContent(text) {
  const parts = [];
  // Combined regex: match <think> blocks OR fenced code blocks
  const combinedRegex = /<think>([\s\S]*?)<\/think>|```(\w*)\n([\s\S]*?)```/g;
  let last = 0;
  let match;

  while ((match = combinedRegex.exec(text)) !== null) {
    if (match.index > last) {
      parts.push({ type: 'text', value: text.slice(last, match.index) });
    }
    if (match[1] !== undefined) {
      // <think> block
      parts.push({ type: 'think', value: match[1].trim() });
    } else {
      // Code block
      parts.push({ type: 'code', language: match[2], value: match[3] });
    }
    last = match.index + match[0].length;
  }

  if (last < text.length) {
    parts.push({ type: 'text', value: text.slice(last) });
  }

  if (parts.length === 0) {
    parts.push({ type: 'text', value: text });
  }

  return parts;
}

/**
 * Match user input against a list of suggestions (case-insensitive prefix).
 * Returns the matching suggestion's remaining text, or empty string.
 */
export function matchSuggestion(input, suggestions) {
  if (!input || input.length < 2) return '';
  const lower = input.toLowerCase();
  const match = suggestions.find((s) => s.toLowerCase().startsWith(lower));
  return match ? match.slice(input.length) : '';
}

/**
 * Strip think blocks from a string, return '(continued)' if nothing remains.
 */
export function stripThink(s) {
  const stripped = s.replace(/<think>[\s\S]*?<\/think>\s*/g, '').trim();
  return stripped || '(continued)';
}

/**
 * Prune conversation history to fit within context budget.
 * Mutates the messages array in place and returns it.
 */
export function pruneHistory(messages, opts = {}) {
  const MAX_HISTORY_CHARS = opts.maxChars ?? 102000;
  const MAX_MSG_CHARS = opts.maxMsgChars ?? 3000;
  const MIN_RECENT = opts.minRecent ?? 6;

  // Step 1: Strip think blocks from older messages (keep in most recent 2)
  for (let i = 0; i < messages.length - 2; i++) {
    const m = messages[i];
    if (m.role === 'assistant' && m.content?.includes('<think>')) {
      m.content = stripThink(m.content);
    }
  }

  // Step 2: Truncate bloated individual messages (except last 2)
  for (let i = 0; i < messages.length - 2; i++) {
    if ((messages[i].content || '').length > MAX_MSG_CHARS) {
      messages[i] = {
        ...messages[i],
        content: messages[i].content.slice(0, MAX_MSG_CHARS) + '\n...(truncated)',
      };
    }
  }

  // Step 3: Drop middle messages oldest-first if still over budget
  // Budget counts post-strip size since think blocks never reach the API
  const stripRe = /<think>[\s\S]*?<\/think>\s*/g;
  const apiLen = (m) => (m.role === 'assistant' ? (m.content || '').replace(stripRe, '') : (m.content || '')).length;
  const totalChars = (arr) => arr.reduce((sum, m) => sum + apiLen(m), 0);
  if (totalChars(messages) < MAX_HISTORY_CHARS || messages.length <= MIN_RECENT + 1) return messages;

  const first = messages.slice(0, 1);
  const recent = messages.slice(-MIN_RECENT);
  let middle = messages.slice(1, -MIN_RECENT);

  while (middle.length > 0 && (
    totalChars(first) + totalChars(middle) + totalChars(recent)
  ) > MAX_HISTORY_CHARS) {
    middle.shift();
  }

  messages.length = 0;
  if (middle.length === 0) {
    messages.push(...first, { role: 'system', content: '[earlier messages pruned]' }, ...recent);
  } else {
    messages.push(...first, ...middle, ...recent);
  }
  return messages;
}

/**
 * Build API history snapshot from messages — strips think blocks, preserves all turns.
 */
export function buildApiHistory(messages) {
  return messages
    .filter((m) => m.content)
    .map((m) => ({
      role: m.role,
      content: m.role === 'assistant' ? stripThink(m.content) : m.content,
    }));
}
