import { resolve } from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import dts from 'vite-plugin-dts'
import { defineConfig } from 'vitest/config'
import tsconfig from './tsconfig.json'


export default defineConfig({
  plugins: [
    dts({
      outDir: resolve(__dirname, 'types'),
      entryRoot: './src',
    }),
    // @ts-ignore
    visualizer({ gzipSize: true }),
  ],
  resolve: {
    alias: alias(),
  },
  build: {
    lib: {
      entry: 'src/index.ts',
      formats: ['es'],
    },
  },
  test: {
    setupFiles: [
      './test/matchers.ts',
    ],
  },
})


function alias() {
  const { baseUrl, paths } = tsconfig.compilerOptions
  return Object.fromEntries(
    Object.entries(paths).map(([a, b]) => {
      const m1 = a.match(/(.*)\*$/)!
      console.assert(m1)
      console.assert(!m1[1].includes('*'))
      // m1[1] === ~/
      console.assert(b.length === 1)
      const c = b[0]
      const m2 = c.match(/\.\/(.*)\*$/)!
      console.assert(m2)
      console.assert(!m2.includes('*'))
      return [
        m1[1],
        `${__dirname}/${baseUrl}/${m2[1]}`,
      ]
    })
  )
}
