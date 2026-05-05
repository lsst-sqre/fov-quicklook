import { defineConfig } from "vitest/config"
import { commonConfig } from './vite/common'
import { proxyOptions } from './vite/proxy-config'


export default defineConfig(commonConfig('dev', {
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "src/setupTests",
    mockReset: true,
  },
  server: {
    proxy: {
      ...proxyOptions,
      '/tomoegozen/': {
        target: 'https://tomoe.mtk.ioa.s.u-tokyo.ac.jp',
        rewrite: (path) => path.replace(/^\/tomoegozen\//, '/skyatlas/'),
        secure: false,
      },
    }
  },
}))
