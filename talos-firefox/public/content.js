// Talos content script — page context extraction
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
