<script>
  let { conversations = [], onLoad, onDelete, onClose } = $props();

  function timeAgo(ts) {
    if (!ts) return '';
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }
</script>

<div class="conv-panel">
  <div class="conv-header">
    <span class="conv-title">Conversations</span>
    <button class="close-btn" onclick={onClose} aria-label="Close">&times;</button>
  </div>

  <div class="conv-list">
    {#if conversations.length === 0}
      <div class="conv-empty">No saved conversations</div>
    {:else}
      {#each conversations as conv}
        <div class="conv-item">
          <button class="conv-load" onclick={() => onLoad(conv)}>
            <span class="conv-item-title">{conv.title || 'Untitled'}</span>
            <span class="conv-meta">{conv.messageCount || 0} msgs &middot; {timeAgo(conv.updatedAt)}</span>
          </button>
          <button class="conv-delete" onclick={() => onDelete(conv)} aria-label="Delete" title="Delete">&times;</button>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .conv-panel {
    border-bottom: 1px solid var(--forge-light);
    max-height: 300px;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  .conv-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid var(--forge-light);
  }

  .conv-title {
    font-size: 12px;
    font-weight: 600;
    color: var(--bronze);
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 16px;
    padding: 0 4px;
    line-height: 1;
  }

  .close-btn:hover {
    color: var(--warm);
  }

  .conv-list {
    overflow-y: auto;
    flex: 1;
  }

  .conv-empty {
    padding: 16px;
    text-align: center;
    color: var(--muted);
    font-size: 12px;
  }

  .conv-item {
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--forge-light);
  }

  .conv-load {
    flex: 1;
    background: none;
    border: none;
    padding: 8px 12px;
    cursor: pointer;
    text-align: left;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .conv-load:hover {
    background: var(--forge-light);
  }

  .conv-item-title {
    font-size: 12px;
    color: var(--warm);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .conv-meta {
    font-size: 10px;
    color: var(--muted);
  }

  .conv-delete {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 4px 8px;
    font-size: 14px;
    flex-shrink: 0;
  }

  .conv-delete:hover {
    color: var(--oxidized);
  }
</style>
