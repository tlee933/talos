<script>
  let { code = '', language = '' } = $props();
  let copied = $state(false);

  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      copied = true;
      setTimeout(() => (copied = false), 1500);
    });
  }
</script>

<div class="code-block">
  {#if language}
    <div class="code-header">
      <span class="language">{language}</span>
      <button class="copy-btn" onclick={copy}>
        {copied ? 'copied' : 'copy'}
      </button>
    </div>
  {:else}
    <div class="code-header">
      <span></span>
      <button class="copy-btn" onclick={copy}>
        {copied ? 'copied' : 'copy'}
      </button>
    </div>
  {/if}
  <pre><code>{code}</code></pre>
</div>

<style>
  .code-block {
    margin: 6px 0;
    border: 1px solid var(--muted);
    border-radius: 6px;
    overflow: hidden;
    background: var(--forge);
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 10px;
    background: var(--forge-light);
    border-bottom: 1px solid var(--muted);
    font-size: 11px;
  }

  .language {
    color: var(--gold);
    font-weight: 600;
  }

  .copy-btn {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 3px;
  }

  .copy-btn:hover {
    color: var(--warm);
    background: var(--forge);
  }

  pre {
    margin: 0;
    padding: 10px;
    overflow-x: auto;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 12px;
    line-height: 1.5;
  }

  code {
    color: var(--warm);
  }
</style>
