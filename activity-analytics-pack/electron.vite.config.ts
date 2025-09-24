import { defineConfig } from 'electron-vite';
import { resolve } from 'path';

export default defineConfig({
  main: {
    build: {
      outDir: 'dist/main',
      rollupOptions: {
        
        input: {
          index: resolve(__dirname, 'src/main/index.ts'),
          'worker/dataWorker': resolve(__dirname, 'src/worker/dataWorker.ts'),
        },
        external: ['better-sqlite3'],
      },
    },
  },
  preload: {
    build: { outDir: 'dist/preload' },
  },
  renderer: {
    root: resolve(__dirname, 'src/renderer'),
    build: { outDir: 'dist/renderer' },
    optimizeDeps: { include: ['chart.js', '@fortawesome/fontawesome-free'] }
  },
});