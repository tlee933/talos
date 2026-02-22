<script>
  import { onMount } from 'svelte';
  import ContextChip from './ContextChip.svelte';
  import { matchSuggestion } from '../utils.js';

  let { onSend, disabled = false, context = null, contextMode = null, onDismissContext, messages = [] } = $props();
  let text = $state('');
  let textarea;

  const BASE_SUGGESTIONS = [
    'Summarize this page',
    'Explain this code',
    'What does this do?',
    'Write a function that ',
    'Help me understand ',
    'How do I ',
    'Fix this bug',
    'Refactor this to ',
    'What are the key points?',
    'Compare these approaches',
    'Give me an example of ',
    'Translate this to ',
    'Debug this error',
    'Optimize this code',
    'What is the difference between ',
  ];

  // Build context-aware follow-up suggestions from last assistant response
  let contextSuggestions = $derived.by(() => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant' && m.content);
    if (!last) return [];
    const c = last.content.toLowerCase();
    const follow = [];

    // Code-related follow-ups
    if (c.includes('```') || c.includes('function') || c.includes('class ')) {
      follow.push('Explain this step by step', 'Can you add error handling?', 'Write tests for this', 'Can you optimize this?', 'Show me a different approach');
    }
    // List/comparison follow-ups
    if (c.includes('1.') || c.includes('- ') || c.includes('* ')) {
      follow.push('Tell me more about the first one', 'Which do you recommend?', 'Can you elaborate on that?', 'Give me a comparison table');
    }
    // Error/debugging follow-ups
    if (c.includes('error') || c.includes('bug') || c.includes('fix') || c.includes('issue')) {
      follow.push('What caused this error?', 'How do I prevent this?', 'Are there other edge cases?', 'Show me the fix');
    }
    // Explanation follow-ups
    if (c.includes('means') || c.includes('because') || c.includes('essentially')) {
      follow.push('Can you give me an example?', 'Explain it more simply', 'How does this relate to ', 'What are the tradeoffs?');
    }
    // General follow-ups always available after a response
    follow.push('Go deeper on that', 'Can you rewrite that?', 'Thanks, now ', 'What about ');

    return follow;
  });

  // Pick the top preemptive suggestion for empty input
  let preempt = $derived(contextSuggestions.length > 0 ? contextSuggestions[0] : '');

  let ghost = $derived.by(() => {
    // Empty field after a conversation — show preemptive suggestion
    if (!text && preempt) return preempt;
    // Context-aware suggestions take priority
    const all = [...contextSuggestions, ...BASE_SUGGESTIONS];
    return matchSuggestion(text, all);
  });

  function handleKeydown(e) {
    if (e.key === 'Tab' && ghost) {
      e.preventDefault();
      text = text + ghost;
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  let inputBar;

  function spawnFlames() {
    if (!inputBar) return;
    const rect = inputBar.getBoundingClientRect();
    const emojis = ['🔥', '🔥', '🔥', '🔥', '✨', '💥', '⚡'];
    // Staggered waves for sustained burn
    for (let wave = 0; wave < 2; wave++) {
      setTimeout(() => {
        for (let i = 0; i < 6; i++) {
          const el = document.createElement('span');
          el.textContent = emojis[Math.floor(Math.random() * emojis.length)];
          el.style.cssText = `
            position: fixed;
            left: ${rect.left + Math.random() * rect.width}px;
            top: ${rect.top - Math.random() * 10}px;
            font-size: ${18 + Math.random() * 22}px;
            pointer-events: none;
            z-index: 9999;
            animation: flame ${1.2 + Math.random() * 1.0}s ease-out forwards;
            --dx: ${(Math.random() - 0.5) * 100}px;
            --dy: ${160 + Math.random() * 120}px;
          `;
          document.body.appendChild(el);
          setTimeout(() => el.remove(), 2500);
        }
      }, wave * 150);
    }
  }

  function send() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    spawnFlames();
    onSend(trimmed);
    text = '';
  }

  // Re-focus textarea whenever it becomes enabled (after streaming ends)
  $effect(() => {
    if (!disabled && textarea) {
      textarea.focus();
    }
  });

  onMount(() => {
    // Inject flame keyframes (Svelte scoped styles can't do global @keyframes)
    if (!document.getElementById('talos-flame-css')) {
      const style = document.createElement('style');
      style.id = 'talos-flame-css';
      style.textContent = `
        @keyframes flame {
          0% { opacity: 1; transform: translateY(0) translateX(0) scale(1) rotate(0deg); }
          30% { opacity: 1; transform: translateY(calc(var(--dy) * -0.3)) translateX(calc(var(--dx) * 0.4)) scale(1.2) rotate(8deg); }
          100% { opacity: 0; transform: translateY(calc(var(--dy) * -1)) translateX(var(--dx)) scale(0) rotate(-12deg); }
        }
      `;
      document.head.appendChild(style);
    }

    // Sidebar panel doesn't have window focus on mount — listen for it
    const focusInput = () => textarea?.focus();
    window.addEventListener('focus', focusInput);
    setTimeout(focusInput, 100);
    return () => window.removeEventListener('focus', focusInput);
  });
</script>

<div class="input-bar" bind:this={inputBar}>
  {#if context}
    <ContextChip {context} mode={contextMode} onDismiss={onDismissContext} />
  {/if}
  <div class="row">
    <div class="textarea-wrap">
      <textarea
        bind:this={textarea}
        bind:value={text}
        onkeydown={handleKeydown}
        placeholder={preempt ? '' : 'Ask Talos...'}
        rows="1"
        {disabled}
      ></textarea>
      {#if ghost}
        <div class="ghost" aria-hidden="true">
          <span class="typed">{text}</span><span class="suggestion">{ghost}</span>
        </div>
      {/if}
    </div>
    <button onclick={send} disabled={disabled || !text.trim()} aria-label="Send">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 2L11 13M22 2L15 22L11 13M22 2L2 9L11 13" />
      </svg>
    </button>
  </div>
</div>

<style>
  .input-bar {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 8px 12px;
    border-top: 1px solid var(--forge-light);
    background: var(--forge);
  }

  .row {
    display: flex;
    gap: 8px;
  }

  .textarea-wrap {
    flex: 1;
    position: relative;
  }

  textarea {
    width: 100%;
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

  .ghost {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    padding: 8px 10px;
    border: 1px solid transparent;
    font-family: inherit;
    font-size: 13px;
    line-height: 1.4;
    pointer-events: none;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow: hidden;
  }

  .ghost .typed {
    visibility: hidden;
  }

  .ghost .suggestion {
    color: var(--muted);
    opacity: 0.5;
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
