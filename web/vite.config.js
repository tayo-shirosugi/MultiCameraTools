import { defineConfig } from 'vite'

export default defineConfig({
  // Use relative base so it works on GitHub Pages without extra setup
  base: './',
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
