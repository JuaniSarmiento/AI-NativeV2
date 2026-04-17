function defaultWsUrl(): string {
  // Derive scheme from page protocol: HTTPS pages MUST use wss:// to avoid
  // mixed-content. Connect to the same origin so nginx can proxy /ws/* to api.
  const scheme = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = typeof window !== 'undefined' ? window.location.host : 'localhost:5174';
  return `${scheme}://${host}`;
}

export const config = {
  apiUrl: import.meta.env.VITE_API_URL || '/api',
  wsUrl: import.meta.env.VITE_WS_URL || defaultWsUrl(),
} as const;
