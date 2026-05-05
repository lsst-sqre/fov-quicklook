import { fits } from "@stellar-globe/stellar-globe"

export interface Header { [key: string]: any }


export interface CardTypes {
  number: number
  string: string
  boolean: boolean
}


export function card<T extends keyof CardTypes>(
  header: Header, key: string, type: T, defaultValue?: any,
): CardTypes[T] {
  let value = header[key]
  if (value === undefined) {
    value = defaultValue
  }
  if (typeof value !== type) {
    throw new Error(`Type mismatch: ${value} for ${key}`)
  }
  return value
}


export interface MakeTileRequest {
  header: Header
  ab: ArrayBuffer
}

export interface MakeTileResponse {
  type: string
  tiles: { [path: string]: ArrayBuffer }
}


// function makeTiles({ header, ab }: MakeTileRequest): MakeTileResponse {
//   const tileSize = 256
//   const bitpix = card(header, 'BITPIX', 'number')
//   let nx = card(header, 'NAXIS1', 'number')
//   let ny = card(header, 'NAXIS2', 'number')
//   let array = convertToFloat32(ab, bitpix)

//   const tiles: MakeTileResponse["tiles"] = {}

//   for (let zi = 0; zi <= 8; ++zi) {
//     for (let yi = 0; yi * tileSize < ny; ++yi) {
//       for (let xi = 0; xi * tileSize < nx; ++xi) {
//         const tile = new Float32Array(tileSize * tileSize)
//         const y0 = yi * tileSize
//         const x0 = xi * tileSize
//         for (let y = 0; y < tileSize && y + y0 < ny; ++y) {
//           for (let x = 0; x < tileSize && x + x0 < nx; ++x) {
//             tile[y * tileSize + x] = array[(y0 + y) * nx + (x0 + x)]
//           }
//         }
//         tiles[`${zi}/${yi}/${xi}`] = tile.buffer
//       }
//     }
//     [array, ny, nx] = halfShrink(array, ny, nx)
//   }

//   return { type: 'float32', tiles }
// }

function halfShrink(a: Float32Array, ny: number, nx: number): [Float32Array, number, number] {
  const ny0 = (ny + 1) >> 1 << 1 // safe region
  const nx0 = (nx + 1) >> 1 << 1
  const b = new Float32Array((ny0 * nx0) >> 2)
  for (let y = 0; y < ny0; ++y) {
    for (let x = 0; x < nx0; ++x) {
      b[(y >> 1) * (nx0 >> 1) + (x >> 1)] += 0.25 * a[y * nx + x]
    }
  }
  return [b, ny0 >> 1, nx0 >> 1]
}

function convertToFloat32(ab: ArrayBuffer, bitpix: number) {
  switch (bitpix) {
    case -32:
      return new Float32Array(ab)
    case -64:
      return new Float32Array(new Float64Array(ab))
    default:
      throw Error(`Unsupported BITPIX: ${bitpix}`)
  }
}


export function buildMaskTiles(hdu: fits.Hdu, bitMask: number): { [path: string]: Uint8ClampedArray } {
  const tileSize = 256
  const bitpix = card(hdu.header, 'BITPIX', 'number')
  let nx = card(hdu.header, 'NAXIS1', 'number')
  let ny = card(hdu.header, 'NAXIS2', 'number')

  if (bitpix !== 8) {
    throw new Error(`Unsupported BITPIX: ${bitpix}`)
  }

  const source = new Uint8Array(hdu.data)
  let array = new Float32Array(ny * nx)

  for (let y = 0; y < ny; ++y) {
    for (let x = 0; x < nx; ++x) {
      array[y * nx + x] = (source[y * nx + x] & bitMask) ? 1 : 0
    }
  }

  const tiles: { [path: string]: Uint8ClampedArray } = {}

  for (let zi = 0; zi <= 8; ++zi) {
    for (let yi = 0; yi * tileSize < ny; ++yi) {
      for (let xi = 0; xi * tileSize < nx; ++xi) {
        const tile = new Uint8ClampedArray(2 * tileSize * tileSize)
        const y0 = yi * tileSize
        const x0 = xi * tileSize
        for (let y = 0; y < tileSize && y + y0 < ny; ++y) {
          for (let x = 0; x < tileSize && x + x0 < nx; ++x) {
            tile[2 * (y * tileSize + x)] = 256
            tile[2 * (y * tileSize + x) + 1] = 256 * array[(y0 + y) * nx + (x0 + x)]
            // tile[y * tileSize + x] = 256
          }
        }
        tiles[`${zi}/${yi}/${xi}`] = tile
      }
    }
    // @ts-ignore
    [array, ny, nx] = halfShrink(array, ny, nx)
  }

  return tiles
}


// const ctx: Worker = self as any
// ctx.addEventListener('message', (e) => {
//   const req: IMakeTileRequest = e.data
//   const res = makeTiles(req)
//   ctx.postMessage(res, Object.values(res.tiles))
//   // @ts-ignore
//   ctx.close()
// })
