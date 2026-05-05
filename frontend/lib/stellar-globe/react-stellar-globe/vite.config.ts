import react from '@vitejs/plugin-react'
import path from 'node:path'
import { defineConfig } from 'vite'
import dts from 'vite-plugin-dts'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    dts({
      outDir: path.resolve(__dirname, 'types'),
      entryRoot: './src',
    }),
  ],
  build: {
    sourcemap: true,
    lib: {
      entry: path.resolve(__dirname, 'src/index.ts'),
      formats: ['es'],
      fileName: (format) => `react-stellar-globe.${format}.js`,
    },
    rollupOptions: {
      external: ['react', 'react-dom', '@stellar-globe/stellar-globe'],
    },
  },
})
