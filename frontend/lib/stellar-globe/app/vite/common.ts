import react from "@vitejs/plugin-react"
import { visualizer } from 'rollup-plugin-visualizer'
import { UserConfig } from "vitest/config"


export function commonConfig(configName: string, options: UserConfig = {}): UserConfig {
  const plugins: UserConfig['plugins'] = [
    ...(options.plugins || []),
    react(),
    visualizer({ gzipSize: true, filename: `stats/${configName}.html` }),
  ]

  const build: UserConfig['build'] = {
    ...options.build,
    outDir: `dist/${configName}`,
    sourcemap: true,
  }

  const css: UserConfig['css'] = {
    ...options.css,
    modules: {
      localsConvention: 'camelCaseOnly',
    },
  }

  return {
    ...options,
    base: './',
    plugins,
    build,
    css,
    envDir: './vite/env',
  }
}
