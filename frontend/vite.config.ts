import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const backendHttpTarget = process.env.VITE_BACKEND_PROXY_TARGET ?? 'http://localhost:8011'
const backendWsTarget = process.env.VITE_BACKEND_WS_TARGET ?? 'ws://localhost:8011'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backendHttpTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: backendWsTarget,
        ws: true,
      },
    },
  },
})
