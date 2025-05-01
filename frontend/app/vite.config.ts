import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { getGafaelfawrToken } from './vite.proxysettings'


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
        target: 'https://usdf-rsp-dev.slac.stanford.edu',
        secure: true,
        changeOrigin: true,
        cookieDomainRewrite: 'localhost',
        headers: {
          Cookie: `gafaelfawr=${getGafaelfawrToken()}`,
        },
        ws: true,
      },
    },
    watch: {
      ignored: ['**/node_modules/**'],
    },
  },
  css: {
    modules: {
      localsConvention: 'camelCaseOnly',
    },
  },
})
