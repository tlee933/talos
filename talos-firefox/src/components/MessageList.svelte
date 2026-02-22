<script>
  import { tick } from 'svelte';
  import Message from './Message.svelte';

  let { messages = [], streamingId = null } = $props();
  let container;

  // Track the last assistant message content for streaming scroll
  let lastContent = $derived(
    messages.length > 0 ? messages[messages.length - 1].content : ''
  );

  $effect(() => {
    // Trigger on length change or content change (streaming tokens)
    messages.length;
    lastContent;
    if (container) {
      tick().then(() => {
        container.scrollTop = container.scrollHeight;
      });
    }
  });
</script>

<div class="message-list" bind:this={container}>
  {#if messages.length === 0}
    <div class="empty">
      <div class="logo">T</div>
      <p>Ask Talos anything</p>
    </div>
  {:else}
    {#each messages as msg, i (i)}
      <Message
        role={msg.role}
        content={msg.content}
        streaming={msg.role === 'assistant' && streamingId !== null && i === messages.length - 1}
      />
    {/each}
  {/if}
</div>

<style>
  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 12px;
    color: var(--muted);
  }

  .logo {
    font-family: serif;
    font-size: 48px;
    font-weight: bold;
    color: var(--gold);
    opacity: 0.5;
  }

  .empty p {
    font-size: 13px;
  }
</style>
