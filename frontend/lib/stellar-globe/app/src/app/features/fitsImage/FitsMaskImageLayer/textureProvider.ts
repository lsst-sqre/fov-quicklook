import { Globe, V4, fits, tile } from '@stellar-globe/stellar-globe'
import { MaskMapMeta } from '.'

export class FitsMaskTextureProvider extends tile.AsyncTextureProvider {
  private tracts: tile.Tract[] = []
  private tractName: Map<tile.Tract, string> = new Map()

  constructor(globe: Globe, readonly options: { meta: MaskMapMeta, color: V4, maskBit: number, baseUrl: string }) {
    super(globe)
    const { meta, color } = options
    for (const name of Object.keys(meta.tracts)) {
      const tract = tile.Tract.fromFitsHeader(meta.tracts[name], { maxTileLevel: 2 })
      this.tracts.push(tract)
      this.tractName.set(tract, name)
    }
  }

  async makeTileTexture(...[ref, { fadeIn, sync }]: Parameters<tile.AsyncTextureProvider['makeTileTexture']>): Promise<tile.TileTexture> {
    const revision = this.revision
    const tt = new tile.TileTexture(this, { fadeIn, revision })
    const tractName = this.tractName.get(ref.tract)!
    const path = `${this.options.baseUrl}${tractName}/${ref.level}/${ref.p}/${ref.q}.fits`

    const hdul = await fits.Fits.fetch(path)
    const image = makeImage(hdul[0], this.options.maskBit)

    const gl = this.globe.gl
    const { tileSize } = ref.tract
    tt.tex.bind(() => {
      // gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, tileSize, tileSize, 0, gl.LUMINANCE, gl.UNSIGNED_BYTE, ab)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE_ALPHA, tileSize, tileSize, 0, gl.LUMINANCE_ALPHA, gl.UNSIGNED_BYTE, image)
      if (ref.level === ref.tract.maxTileLevel) {
        gl.generateMipmap(gl.TEXTURE_2D)
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
      }
      if (ref.level === 0) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
      }
    })
    return tt
  }

  walkTracts(callback: (tract: tile.Tract) => void): void {
    for (const tract of this.tracts) {
      callback(tract)
    }
  }
}




function makeImage(hdu: fits.Hdu, bitMask: number): Uint8ClampedArray {
  const bitpix = hdu.card('BITPIX', 'number')
  const nx = hdu.card('NAXIS1', 'number')
  const ny = hdu.card('NAXIS2', 'number')

  if (bitpix !== 8) {
    throw new Error(`Unsupported BITPIX: ${bitpix}`)
  }

  const source = new Uint8Array(hdu.data)
  const tile = new Uint8ClampedArray(2 * ny * nx)

  for (let y = 0; y < ny; ++y) {
    for (let x = 0; x < nx; ++x) {
      tile[2 * (y * nx + x)] = 256
      tile[2 * (y * nx + x) + 1] = 256 * ((source[y * nx + x] & bitMask) ? 1 : 0)
      // tile[2 * (y * nx + x)] = 256
      // tile[2 * (y * nx + x) + 1] = 256 * (source[y * nx + x] & bitMask) ? 1 : 0
    }
  }

  
  
  return tile
}
