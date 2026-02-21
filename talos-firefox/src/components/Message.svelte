<script>
  import CodeBlock from './CodeBlock.svelte';

  let { role = 'user', content = '', streaming = false } = $props();

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
    white-space: pre-wrap;
  }

  .user .bubble {
    background: rgba(205, 127, 50, 0.15);
    border: 1px solid rgba(205, 127, 50, 0.3);
    color: var(--warm);
  }

  .assistant .bubble {
    background: var(--forge-light);
    border: 1px solid rgba(139, 115, 85, 0.3);
    color: var(--warm);
  }

  .text {
    font-size: 13px;
    line-height: 1.5;
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
