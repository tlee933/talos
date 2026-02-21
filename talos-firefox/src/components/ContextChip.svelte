<script>
  let { context, mode, onDismiss } = $props();

  let label = $derived(
    mode === 'selection' ? 'Selection' : mode === 'summarize' ? 'Summarize' : 'Page'
  );

  let title = $derived(
    context?.title
      ? context.title.length > 40
        ? context.title.slice(0, 40) + '...'
        : context.title
      : 'Untitled'
  );
</script>

<div class="chip">
  <span class="badge">{label}</span>
  <span class="title">{title}</span>
  <button class="dismiss" onclick={onDismiss} aria-label="Remove context">&times;</button>
</div>

<style>
  .chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border: 1px solid rgba(205, 127, 50, 0.4);
    border-radius: 6px;
    background: rgba(205, 127, 50, 0.1);
    font-size: 12px;
    line-height: 1.3;
  }

  .badge {
    background: var(--bronze);
    color: var(--forge);
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    flex-shrink: 0;
  }

  .title {
    color: var(--warm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .dismiss {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0 2px;
    flex-shrink: 0;
  }

  .dismiss:hover {
    color: var(--oxidized);
  }
</style>
