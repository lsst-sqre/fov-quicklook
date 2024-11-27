// import type { ConfigFile } from '@rtk-query/codegen-openapi'

const config /*: ConfigFile */ = {
  schemaFile: './openapi.json',
  apiFile: './src/store/api/base.ts',
  apiImport: 'baseApi',
  outputFile: './src/store/api/openapi.ts',
  exportName: 'api',
  hooks: true,
  // filterEndpoints: (name, def) => {
  //   return def.operation.tags.includes('portal')
  // },
}

exports.default = config
// export default config

