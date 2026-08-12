import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // Ensure relative asset paths for Electron file:// protocol
  server: {
    port: 3000,
    open: false,
    cors: true,
  },
  build: {
    outDir: 'dist',
    target: 'esnext',
  }
});
