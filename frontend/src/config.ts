export const config = {
  apiUrl: import.meta.env.VITE_API_URL || '/api',
  wsUrl: import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8001`,
} as const;
