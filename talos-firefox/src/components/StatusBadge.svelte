<script>
  let { connected = false, latency = 0 } = $props();
</script>

<div class="status-badge">
  <span class="dot" class:connected class:disconnected={!connected}></span>
  <span class="label">
    {#if connected}
      connected{#if latency > 0} ({latency}ms){/if}
    {:else}
      disconnected
    {/if}
  </span>
</div>

<style>
  .status-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    font-size: 11px;
    color: var(--muted);
    border-bottom: 1px solid var(--forge-light);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .dot.connected {
    background: var(--verdigris);
    box-shadow: 0 0 4px var(--verdigris);
  }

  .dot.disconnected {
    background: var(--oxidized);
    box-shadow: 0 0 4px var(--oxidized);
  }

  .label {
    text-transform: lowercase;
  }
</style>
