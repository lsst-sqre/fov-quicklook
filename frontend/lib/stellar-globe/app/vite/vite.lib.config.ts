import { PluginOption } from "vite"
import cssInjectedByJsPlugin from 'vite-plugin-css-injected-by-js'
import { defineConfig } from "vitest/config"
import { commonConfig } from './common'


export default defineConfig(commonConfig('lib', {
  plugins: [
    excludeMaterialSymbols(),
    cssInjectedByJsPlugin({
      jsAssetsFilterFunction: output => output.fileName === 'app.es.js'
    }),
  ],
  build: {
    lib: {
      entry: {
        app: `./src/index.ts`,
        commTools: `./src/commTools/index.ts`,
      },
      formats: ['es'],
      fileName: (format, name) => {
        return `${name}.${format}.js`
      },
    },
    rollupOptions: {
      external: ['react', 'react-dom', '@stellar-globe/stellar-globe', '@stellar-globe/react-stellar-globe'],
    },
  },
}))


function excludeMaterialSymbols(): PluginOption {
  return {
    name: 'conditional-css-import',
    transform(_code, id) {
      if (id.endsWith('material-symbols/outlined.css')) {
        return 'export default {}'
      }
    }
  }
}
