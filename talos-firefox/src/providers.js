export const PROVIDERS = [
  { id: 'hive-mind',  label: 'Hive-Mind',  url: 'http://localhost:8090',      model: 'hivecoder-7b',             auth: 'none' },
  { id: 'ollama',     label: 'Ollama',      url: 'http://localhost:11434',     model: 'llama3.1',                 auth: 'none' },
  { id: 'openai',     label: 'OpenAI',      url: 'https://api.openai.com',     model: 'gpt-4o-mini',              auth: 'bearer' },
  { id: 'anthropic',  label: 'Anthropic',   url: 'https://api.anthropic.com',  model: 'claude-sonnet-4-20250514', auth: 'x-api-key' },
  { id: 'custom',     label: 'Custom',      url: '',                            model: '',                         auth: 'bearer' },
];

export const DEFAULT_CONFIG = {
  provider: 'hive-mind',
  apiUrl: 'http://localhost:8090',
  model: 'hivecoder-7b',
  apiKey: '',
  temperature: 0.7,
  maxTokens: 1024,
};
