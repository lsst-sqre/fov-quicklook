import { Zstd } from "@hpcc-js/wasm-zstd"

export async function zstdDecompress(data: Uint8Array): Promise<Uint8Array> {
  const zstd = await get_zstd_module()
  return zstd.decompress(data)
}


let zstd_module: Zstd | null = null
let loading_promise: Promise<Zstd> | null = null


async function get_zstd_module() {
  if (zstd_module) {
    return zstd_module
  }
  if (loading_promise) {
    return loading_promise
  }
  loading_promise = Zstd.load()
  zstd_module = await loading_promise
  return zstd_module
}