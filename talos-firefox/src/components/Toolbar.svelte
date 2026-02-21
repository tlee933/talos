<script>
  import SettingsPanel from './SettingsPanel.svelte';

  let { connected = false, config = {}, tokPerSec = null, onConfigChange } = $props();
  let settingsOpen = $state(false);

  function toggleSettings() {
    settingsOpen = !settingsOpen;
  }

  function handleConfigChange(newConfig) {
    onConfigChange?.(newConfig);
  }

  function closeSettings() {
    settingsOpen = false;
  }
</script>

<div class="toolbar-wrapper">
  <div class="toolbar">
    <span class="dot" class:connected class:disconnected={!connected}></span>
    {#if connected}
      <span class="model">{config.model || 'unknown'}</span>
      <span class="separator">|</span>
      <span class="tok-rate">{tokPerSec != null ? `${tokPerSec} tok/s` : '-- tok/s'}</span>
    {:else}
      <span class="model disconnected-text">disconnected</span>
    {/if}
    <button class="gear-btn" onclick={toggleSettings} aria-label="Settings" class:active={settingsOpen}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </svg>
    </button>
  </div>

  {#if settingsOpen}
    <SettingsPanel {config} onChange={handleConfigChange} onClose={closeSettings} />
  {/if}
</div>

<style>
  .toolbar-wrapper {
    position: relative;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 11px;
    color: var(--muted);
    border-bottom: 1px solid var(--forge-light);
    height: 32px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dot.connected {
    background: var(--verdigris);
    box-shadow: 0 0 4px var(--verdigris);
  }

  .dot.disconnected {
    background: var(--oxidized);
    box-shadow: 0 0 4px var(--oxidized);
  }

  .model {
    color: var(--warm);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .disconnected-text {
    color: var(--oxidized);
    font-weight: 400;
  }

  .separator {
    color: var(--forge-light);
  }

  .tok-rate {
    white-space: nowrap;
  }

  .gear-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 2px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .gear-btn:hover,
  .gear-btn.active {
    color: var(--bronze);
    background: var(--forge-light);
  }
</style>
