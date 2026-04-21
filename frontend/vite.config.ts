/// <reference types="vitest" />

import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': new URL('./src', import.meta.url).pathname,
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5174,
      proxy: {
        '/api': {
          target: process.env.VITE_PROXY_TARGET || env.VITE_PROXY_TARGET || 'http://localhost:8001',
          changeOrigin: true,
        },
        '/ws': {
          target: process.env.VITE_PROXY_TARGET || env.VITE_PROXY_TARGET || 'http://localhost:8001',
          changeOrigin: true,
          ws: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test-setup.ts'],
    },
  };
});
