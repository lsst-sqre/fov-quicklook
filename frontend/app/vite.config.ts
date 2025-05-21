import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { getGafaelfawrToken } from './vite.proxysettings'



// https://vitejs.dev/config/
// @ts-ignore
export default ({ mode }) => {
  // @ts-ignore
  const env = loadEnv(mode, process.cwd())
  const base = env.VITE_BASE_URL // これは /fov-quicklook のような値が入る

  if (!base) {
    throw new Error('VITE_BASE_URL is not set.')
  }

  return defineConfig({
    base: `${base}/`,
    plugins: [
      react(),
    ],
    server: {
      proxy: {
        // '/api/': {
        //   target: 'http://127.0.0.1:29500',
        //   ws: true,
        //   rewrite: (path) => path.replace(/\/api\//, '/fov-quicklook/api/'),
        // },
        [`${base}/api/`]: {
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
}