<script>
  import snarkdown from 'snarkdown';
  import CodeBlock from './CodeBlock.svelte';
  import { sanitize, parseContent } from '../utils.js';

  let { role = 'user', content = '', streaming = false } = $props();

  let parts = $derived(parseContent(content));
</script>

<div class="message" class:user={role === 'user'} class:assistant={role === 'assistant'}>
  <div class="bubble">
    {#each parts as part}
      {#if part.type === 'code'}
        <CodeBlock code={part.value} language={part.language} />
      {:else if part.type === 'think'}
        <details class="think-block" open>
          <summary>thinking</summary>
          <div class="think-content">{part.value}</div>
        </details>
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
    user-select: text;
    cursor: text;
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
    color: var(--gold);
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
    border-left: 3px solid var(--gold);
    padding: 4px 10px;
    margin: 6px 0;
    background: rgba(212, 165, 74, 0.08);
    color: var(--muted);
  }

  .assistant .bubble :global(h1),
  .assistant .bubble :global(h2),
  .assistant .bubble :global(h3),
  .assistant .bubble :global(h4),
  .assistant .bubble :global(h5),
  .assistant .bubble :global(h6) {
    color: var(--gold);
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
    border-bottom: 1px solid rgba(212, 165, 74, 0.3);
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

  .think-block {
    margin: 6px 0;
    border: 1px solid rgba(255, 191, 0, 0.3);
    border-radius: 6px;
    overflow: hidden;
  }

  .think-block summary {
    padding: 4px 10px;
    background: rgba(255, 191, 0, 0.08);
    color: var(--amber);
    font-size: 12px;
    font-style: italic;
    cursor: pointer;
    user-select: none;
  }

  .think-block summary:hover {
    background: rgba(255, 191, 0, 0.15);
  }

  .think-content {
    padding: 8px 10px;
    font-size: 12px;
    line-height: 1.5;
    color: var(--muted);
    font-style: italic;
    white-space: pre-wrap;
  }

  .cursor {
    animation: blink 0.8s step-end infinite;
    color: var(--gold);
    font-weight: bold;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
