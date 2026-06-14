import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: {
    outDir: 'dist',
  },
  server: {
    proxy: {
      '/auth':    'http://localhost:8000',
      '/advice':  'http://localhost:8000',
      '/summary': 'http://localhost:8000',
      '/ingest':  'http://localhost:8000',
      '/health':  'http://localhost:8000',
    },
  },
})
