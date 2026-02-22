<script>
  import SettingsPanel from './SettingsPanel.svelte';

  let { connected = false, config = {}, tokPerSec = null, tokUpdatedAt = 0, modelUsed = '', onConfigChange, onToggleHistory, onNewConversation } = $props();
  let settingsOpen = $state(false);
  let pulsing = $state(false);

  $effect(() => {
    if (tokUpdatedAt > 0) {
      pulsing = true;
      const timer = setTimeout(() => { pulsing = false; }, 600);
      return () => clearTimeout(timer);
    }
  });

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
      <span class="model">{modelUsed || config.model || 'unknown'}</span>
      <span class="separator">|</span>
      <span class="tok-rate" class:pulse={pulsing}>{tokPerSec != null ? `${tokPerSec} tok/s` : '-- tok/s'}</span>
    {:else}
      <span class="model disconnected-text">disconnected</span>
    {/if}
    <button class="icon-btn" onclick={onNewConversation} aria-label="New conversation" title="New conversation">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
    </button>
    <button class="icon-btn" onclick={onToggleHistory} aria-label="Conversations" title="Conversation history">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
      </svg>
    </button>
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
    transition: color 0.3s;
  }

  .tok-rate.pulse {
    color: var(--gold);
  }

  .icon-btn {
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

  .icon-btn:hover {
    color: var(--bronze);
    background: var(--forge-light);
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
