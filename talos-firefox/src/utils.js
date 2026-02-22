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
