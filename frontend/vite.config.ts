import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// Backend-ul FEGBet ruleaza pe portul 8100 (8000 e ocupat pe serverul de productie).
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://localhost:8100'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor stabil intr-un chunk separat, cache-uibil intre deploy-uri.
          vendor: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query', 'axios'],
          motion: ['framer-motion'],
        },
      },
    },
  },
})
