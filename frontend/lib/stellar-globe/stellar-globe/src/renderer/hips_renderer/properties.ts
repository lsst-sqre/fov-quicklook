export type HiPSProperties = { [key: string]: string }

export async function fetchHiPSProperties(baseUrl: string) {
  const url = `${baseUrl}/properties`
  const txt: string = await (await fetch(url)).text()
  const dict: HiPSProperties = {}
  for (const line of txt.split('\n')) {
    if (!line.match(/^\s*#/)) {
      if (line.indexOf('=') >= 0) {
        const [k, v] = line.split('=').map((s) => s.replace(/\s*(.*?)\s*$/, '$1'))
        dict[k] = v
      }
    }
  }
  if (!('hips_order' in dict) || !('hips_tile_width' in dict)) {
    throw new Error(`invalid properties file`)
  }
  return dict
}
