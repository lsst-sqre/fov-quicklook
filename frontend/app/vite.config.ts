import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, UserConfig } from 'vite'

type ProxySettingsModule = {
  getGafaelfawrToken: () => string
}

async function loadProxyTokenReader(mode: string): Promise<(() => string) | null> {
  if (mode !== 'development') {
    return null
  }

  const proxySettingsUrl = new URL('./vite.proxysettings.ts', import.meta.url)
  const proxySettingsPath = fileURLToPath(proxySettingsUrl)
  if (!existsSync(proxySettingsPath)) {
    return null
  }

  const module = await import(proxySettingsUrl.href) as ProxySettingsModule
  return module.getGafaelfawrToken
}

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  const base = env.VITE_BASE_URL // これは /fov-quicklook のような値が入る

  if (!base) {
    throw new Error('VITE_BASE_URL is not set.')
  }

  const getGafaelfawrToken = await loadProxyTokenReader(mode)

  const config: UserConfig = {
    base: `${base}/`,
    plugins: [
      react(),
    ],
    resolve: {
      preserveSymlinks: true,
    },
    css: {
      modules: {
        localsConvention: 'camelCaseOnly',
      },
    },
  }

  if (mode === 'development') {
    const proxyTarget = env.VITE_API_PROXY_TARGET
    if (proxyTarget) {
      return {
        ...config,
        server: {
          proxy: {
            [`${base}/api/`]: {
              target: proxyTarget,
              changeOrigin: true,
              ws: true,
            },
          },
          watch: {
            ignored: ['**/node_modules/**'],
          },
        },
      }
    }

    if (getGafaelfawrToken) {
      return {
        ...config,
        server: {
          proxy: {
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
      }
    }

    return {
      ...config,
      server: {
        watch: {
          ignored: ['**/node_modules/**'],
        },
      },
    }
  }

  return config
})
