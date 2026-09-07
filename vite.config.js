import { defineConfig } from 'vite';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function injectApiBase() {
  let apiBase = '';
  if (process.env.VITE_API_BASE) {
    apiBase = process.env.VITE_API_BASE;
  }
  const snippet = `<script>window.__API_BASE__ = '${apiBase}';</script>`;
  return {
    name: 'inject-api-base',
    transformIndexHtml(html) {
      return html.replace(
        '<script>window.__API_BASE__ = \'\';</script>',
        snippet
      );
    },
  };
}

export default defineConfig({
  root: 'static',
  plugins: [injectApiBase()],
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
