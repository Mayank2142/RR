import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5173, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { outDir: 'dist', emptyOutDir: true, rollupOptions: { output: { manualChunks: {
    charts: ['recharts'], motion: ['framer-motion'], 'react-core': ['react','react-dom','react-router-dom'],
    forms: ['react-hook-form','zod','@hookform/resolvers']
  } } } },
});
