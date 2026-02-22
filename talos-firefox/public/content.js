// Talos content script — page context extraction + keyboard shortcuts
browser.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type !== 'EXTRACT_CONTEXT') return;

  const mode = msg.mode;
  const context = {
    title: document.title,
    url: location.href,
  };

  if (mode === 'selection') {
    context.selection = window.getSelection().toString();
  } else {
    // "page" or "summarize" mode — full page data
    context.text = document.body.innerText.slice(0, 8000);
    context.headings = [...document.querySelectorAll('h1,h2,h3')]
      .map((h) => h.textContent.trim())
      .slice(0, 20);
    context.meta =
      document.querySelector('meta[name="description"]')?.content || '';
  }

  sendResponse(context);
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (!e.ctrlKey || !e.shiftKey) return;

  if (e.key === 'S' || e.key === 's') {
    // Ctrl+Shift+S — send selection to Talos
    const selection = window.getSelection().toString();
    if (!selection) return;
    e.preventDefault();
    browser.runtime.sendMessage({
      type: 'CONTENT_SHORTCUT',
      mode: 'selection',
      context: {
        title: document.title,
        url: location.href,
        selection,
      },
    });
  } else if (e.key === 'P' || e.key === 'p') {
    // Ctrl+Shift+P — send full page to Talos
    e.preventDefault();
    browser.runtime.sendMessage({
      type: 'CONTENT_SHORTCUT',
      mode: 'page',
      context: {
        title: document.title,
        url: location.href,
        text: document.body.innerText.slice(0, 8000),
        headings: [...document.querySelectorAll('h1,h2,h3')]
          .map((h) => h.textContent.trim())
          .slice(0, 20),
        meta:
          document.querySelector('meta[name="description"]')?.content || '',
      },
    });
  }
});
