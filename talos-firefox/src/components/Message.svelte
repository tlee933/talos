<script>
  import snarkdown from 'snarkdown';
  import CodeBlock from './CodeBlock.svelte';

  let { role = 'user', content = '', streaming = false } = $props();

  const ALLOWED_TAGS = new Set([
    'strong', 'em', 'a', 'code', 'ul', 'ol', 'li', 'p', 'br',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'del',
  ]);

  function sanitize(html) {
    // Strip tags not in allowlist, keep only href on <a>
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

  function parseContent(text) {
    const parts = [];
    const codeRegex = /```(\w*)\n([\s\S]*?)```/g;
    let last = 0;
    let match;

    while ((match = codeRegex.exec(text)) !== null) {
      if (match.index > last) {
        parts.push({ type: 'text', value: text.slice(last, match.index) });
      }
      parts.push({ type: 'code', language: match[1], value: match[2] });
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

  let parts = $derived(parseContent(content));
</script>

<div class="message" class:user={role === 'user'} class:assistant={role === 'assistant'}>
  <div class="bubble">
    {#each parts as part}
      {#if part.type === 'code'}
        <CodeBlock code={part.value} language={part.language} />
      {:else if role === 'assistant'}
        <span class="markdown">{@html sanitize(snarkdown(part.value))}</span>
      {:else}
        <span class="text">{part.value}</span>
      {/if}
    {/each}
    {#if streaming}
      <span class="cursor">|</span>
    {/if}
  </div>
</div>

<style>
  .message {
    display: flex;
    padding: 4px 12px;
  }

  .message.user {
    justify-content: flex-end;
  }

  .message.assistant {
    justify-content: flex-start;
  }

  .bubble {
    max-width: 85%;
    padding: 8px 12px;
    border-radius: 8px;
    word-wrap: break-word;
  }

  .user .bubble {
    background: rgba(205, 127, 50, 0.15);
    border: 1px solid rgba(205, 127, 50, 0.3);
    color: var(--warm);
    white-space: pre-wrap;
  }

  .assistant .bubble {
    background: var(--forge-light);
    border: 1px solid rgba(139, 115, 85, 0.3);
    color: var(--warm);
  }

  .text {
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
  }

  .markdown {
    font-size: 13px;
    line-height: 1.5;
  }

  /* Markdown styles for assistant messages */
  .assistant .bubble :global(strong) {
    color: var(--bronze);
  }

  .assistant .bubble :global(em) {
    font-style: italic;
  }

  .assistant .bubble :global(a) {
    color: var(--verdigris);
    text-decoration: underline;
  }

  .assistant .bubble :global(a:hover) {
    color: var(--amber);
  }

  .assistant .bubble :global(ul),
  .assistant .bubble :global(ol) {
    padding-left: 20px;
    margin: 4px 0;
  }

  .assistant .bubble :global(li) {
    margin: 2px 0;
  }

  .assistant .bubble :global(blockquote) {
    border-left: 3px solid var(--bronze);
    padding: 4px 10px;
    margin: 6px 0;
    background: rgba(205, 127, 50, 0.08);
    color: var(--muted);
  }

  .assistant .bubble :global(h1),
  .assistant .bubble :global(h2),
  .assistant .bubble :global(h3),
  .assistant .bubble :global(h4),
  .assistant .bubble :global(h5),
  .assistant .bubble :global(h6) {
    color: var(--bronze);
    margin: 8px 0 4px;
    line-height: 1.3;
  }

  .assistant .bubble :global(h1) { font-size: 16px; }
  .assistant .bubble :global(h2) { font-size: 15px; }
  .assistant .bubble :global(h3) { font-size: 14px; }
  .assistant .bubble :global(h4),
  .assistant .bubble :global(h5),
  .assistant .bubble :global(h6) { font-size: 13px; }

  .assistant .bubble :global(code) {
    background: var(--forge-light);
    padding: 1px 5px;
    border-radius: 3px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 12px;
  }

  .assistant .bubble :global(hr) {
    border: none;
    border-top: 1px solid var(--muted);
    margin: 8px 0;
  }

  .assistant .bubble :global(p) {
    margin-bottom: 6px;
  }

  .assistant .bubble :global(p:last-child) {
    margin-bottom: 0;
  }

  .assistant .bubble :global(del) {
    text-decoration: line-through;
    opacity: 0.7;
  }

  .cursor {
    animation: blink 0.8s step-end infinite;
    color: var(--bronze);
    font-weight: bold;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
