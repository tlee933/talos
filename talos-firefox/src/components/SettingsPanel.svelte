<script>
  import { PROVIDERS } from '../providers.js';

  let { config = {}, onChange, onClose } = $props();

  let provider = $state('hive-mind');
  let apiUrl = $state('');
  let model = $state('');
  let apiKey = $state('');
  let temperature = $state(0.7);
  let maxTokens = $state(1024);
  let showKey = $state(false);

  // Sync local state when config prop changes (e.g. CONFIG_LOADED from background)
  $effect(() => {
    provider = config.provider || 'hive-mind';
    apiUrl = config.apiUrl || '';
    model = config.model || '';
    apiKey = config.apiKey || '';
    temperature = config.temperature ?? 0.7;
    maxTokens = config.maxTokens ?? 1024;
  });

  function selectPreset(id) {
    provider = id;
    const preset = PROVIDERS.find((p) => p.id === id);
    if (preset) {
      apiUrl = preset.url;
      model = preset.model;
    }
    emit();
  }

  function emit() {
    onChange?.({ provider, apiUrl, model, apiKey, temperature, maxTokens });
  }

  function handleClickOutside(e) {
    if (e.target.closest('.settings-panel') || e.target.closest('.gear-btn')) return;
    onClose?.();
  }
</script>

<svelte:window onclick={handleClickOutside} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="settings-panel" onclick={(e) => e.stopPropagation()}>
  <div class="presets">
    {#each PROVIDERS as p}
      <button
        class="preset-btn"
        class:active={provider === p.id}
        onclick={() => selectPreset(p.id)}
      >
        {p.label}
      </button>
    {/each}
  </div>

  <label class="field">
    <span class="field-label">URL</span>
    <input type="text" bind:value={apiUrl} oninput={emit} placeholder="http://localhost:8090" />
  </label>

  <label class="field">
    <span class="field-label">Model</span>
    <input type="text" bind:value={model} oninput={emit} placeholder="model name" />
  </label>

  <label class="field">
    <span class="field-label">API Key</span>
    <div class="key-row">
      <input
        type={showKey ? 'text' : 'password'}
        bind:value={apiKey}
        oninput={emit}
        placeholder="optional"
      />
      <button class="toggle-key" onclick={() => (showKey = !showKey)}>
        {showKey ? 'hide' : 'show'}
      </button>
    </div>
  </label>

  <label class="field">
    <span class="field-label">Temperature</span>
    <div class="slider-row">
      <input
        type="range"
        min="0"
        max="2"
        step="0.1"
        bind:value={temperature}
        oninput={emit}
      />
      <span class="slider-value">{temperature.toFixed(1)}</span>
    </div>
  </label>

  <label class="field">
    <span class="field-label">Max Tokens</span>
    <input type="number" bind:value={maxTokens} oninput={emit} min="1" max="128000" />
  </label>
</div>

<style>
  .settings-panel {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--forge);
    border: 1px solid var(--forge-light);
    border-top: none;
    padding: 10px 12px;
    z-index: 100;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .presets {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .preset-btn {
    padding: 3px 8px;
    font-size: 10px;
    border: 1px solid var(--forge-light);
    border-radius: 4px;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
  }

  .preset-btn:hover {
    border-color: var(--bronze);
    color: var(--warm);
  }

  .preset-btn.active {
    background: var(--bronze);
    color: var(--forge);
    border-color: var(--bronze);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .field-label {
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .field input[type='text'],
  .field input[type='password'],
  .field input[type='number'] {
    background: var(--forge-light);
    border: 1px solid var(--forge-light);
    border-radius: 4px;
    color: var(--warm);
    padding: 5px 8px;
    font-size: 12px;
    font-family: inherit;
    outline: none;
    width: 100%;
  }

  .field input:focus {
    border-color: var(--bronze);
  }

  .key-row {
    display: flex;
    gap: 4px;
  }

  .key-row input {
    flex: 1;
    min-width: 0;
  }

  .toggle-key {
    padding: 4px 8px;
    font-size: 10px;
    background: var(--forge-light);
    border: 1px solid var(--forge-light);
    border-radius: 4px;
    color: var(--muted);
    cursor: pointer;
    white-space: nowrap;
  }

  .toggle-key:hover {
    color: var(--bronze);
  }

  .slider-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .slider-row input[type='range'] {
    flex: 1;
    -webkit-appearance: none;
    appearance: none;
    height: 4px;
    background: var(--forge-light);
    border-radius: 2px;
    outline: none;
  }

  .slider-row input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--bronze);
    cursor: pointer;
  }

  .slider-row input[type='range']::-moz-range-thumb {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--bronze);
    cursor: pointer;
    border: none;
  }

  .slider-value {
    font-size: 11px;
    color: var(--warm);
    min-width: 2em;
    text-align: right;
  }
</style>
