import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

let getGafaelfawrToken: (() => string) | null = null

try {
  // @ts-ignore
  getGafaelfawrToken = require('./vite.proxysettings').getGafaelfawrToken
} catch (e) {
  // vite.proxysettings.ts が見つからない場合はスキップ（production ビルド時など）
}

// https://vitejs.dev/config/
// @ts-ignore
export default ({ mode }) => {
  // @ts-ignore
  const env = loadEnv(mode, process.cwd())
  const base = env.VITE_BASE_URL // これは /fov-quicklook のような値が入る

  if (!base) {
    throw new Error('VITE_BASE_URL is not set.')
  }

  const config = {
    base: `${base}/`,
    plugins: [
      react(),
    ],
    css: {
      modules: {
        localsConvention: 'camelCaseOnly' as const,
      },
    },
  }

  if (mode === 'development' && getGafaelfawrToken) {
    return defineConfig({
      ...config,
      server: {
        proxy: {
          // [`${base}/api/`]: {
          //   target: 'http://127.0.0.1:9500',
          //   ws: true,
          //   // rewrite: (path) => path.replace(/\/api\//, '/fov-quicklook/api/'),
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
    } as any)
  }

  return defineConfig(config as any)
}