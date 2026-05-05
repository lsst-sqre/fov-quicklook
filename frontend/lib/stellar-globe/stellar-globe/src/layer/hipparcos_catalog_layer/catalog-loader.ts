import { deg2rad, SkyCoord } from '~/lib/angle'; // I don't know why but this import cannot use absolute path.
import { V4 } from "~/types"

export type RequestMessage = {
  dataRepository: string
}

export type ResponseMessage = {
  buffer: ArrayBuffer
  end: boolean
}


self.addEventListener('message', async e => {
  const request: RequestMessage = e.data
  try {
    await main(request)
  }
  finally {
    self.close()
  }
})


async function main({ dataRepository }: RequestMessage) {
  const jsArray: number[] = []
  const index: string[] = await (await fetch(`${dataRepository}/hipparcos-catalog/index.json`)).json()
  const catalogParts = index.map(f => `${dataRepository}/hipparcos-catalog/${f}`)

  for (let i = 0; i < catalogParts.length; ++i) {
    const catalogPart = catalogParts[i]
    // @ts-ignore
    const data = await (await fetch(catalogPart)).json()
    loadPartialCatalog(data, jsArray)
    const buffer = (new Float32Array(jsArray)).buffer
    const res: ResponseMessage = {
      buffer,
      end: i === catalogParts.length - 1
    }
    // Adding webworker to compilerOptions.lib fixes type on postMessage,
    // but brings in a bunch of other errors.
    // @ts-ignore
    self.postMessage(res, [buffer])
  }
}


function mag2flux(m: number) {
  return Math.pow(10, -m / 2.5)
}

type Star = [number, number, number, number]


function loadPartialCatalog(catalog: Star[], addTo: number[]) {
  const fluxSirius = mag2flux(-1.47)
  const sizeSirius = deg2rad(5)
  for (const s of catalog) {
    const xyz = SkyCoord.fromRad(s[0], s[1]).xyz
    const color: V4 = [0.75, 0.75, 1, 1]
    const flux = mag2flux(s[2])
    const size = sizeSirius * Math.sqrt(flux / fluxSirius)
    addTo.push(...xyz, size, ...color)
  }
}
