<script>
  let { onSend, disabled = false } = $props();
  let text = $state('');

  function handleKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function send() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    text = '';
  }
</script>

<div class="input-bar">
  <textarea
    bind:value={text}
    onkeydown={handleKeydown}
    placeholder="Ask Talos..."
    rows="1"
    {disabled}
  ></textarea>
  <button onclick={send} disabled={disabled || !text.trim()} aria-label="Send">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" />
    </svg>
  </button>
</div>

<style>
  .input-bar {
    display: flex;
    gap: 8px;
    padding: 8px 12px;
    border-top: 1px solid var(--forge-light);
    background: var(--forge);
  }

  textarea {
    flex: 1;
    resize: none;
    border: 1px solid var(--muted);
    border-radius: 6px;
    background: var(--forge-light);
    color: var(--warm);
    padding: 8px 10px;
    font-family: inherit;
    font-size: 13px;
    line-height: 1.4;
    outline: none;
    min-height: 36px;
    max-height: 120px;
    overflow-y: auto;
  }

  textarea:focus {
    border-color: var(--bronze);
  }

  textarea:disabled {
    opacity: 0.5;
  }

  textarea::placeholder {
    color: var(--muted);
  }

  button {
    align-self: flex-end;
    width: 36px;
    height: 36px;
    border: none;
    border-radius: 6px;
    background: var(--bronze);
    color: var(--forge);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  button:hover:not(:disabled) {
    background: var(--amber);
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }
</style>
