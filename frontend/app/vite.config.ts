import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'


// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    react(),
  ],
  server: {
    proxy: {
      '/api/': {
        target: 'http://127.0.0.1:29500',
        ws: true,
        rewrite: (path) => path.replace(/\/api\//, '/fov-quicklook/api/'),
      },
      '/fov-quicklook/api/': {
        target: 'http://127.0.0.1:29500',
        ws: true,
        // rewrite: (path) => path.replace(/^\/fov-quicklook\/api\//, '/api/'),
      },
    },
    watch: {
      ignored: ['**/node_modules/**'],
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: "modern-compiler",
        charset: false,
      },
    },
    modules: {
      localsConvention: 'camelCaseOnly',
    },
  },
})
