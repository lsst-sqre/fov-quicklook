import { Cache, Globe, ReleaseCallbacks, Tract, V2, angle, tile } from "@stellar-globe/stellar-globe"
import npyjs from 'npyjs'
import { QuicklookMetadata } from "../../../store/api/openapi"
import { RubinImageFilter, RubinImageFilterParams } from "./ImaegFilter"


const TILE_SIZE = 256


type Npy = Awaited<ReturnType<npyjs["load"]>>


export class QuicklookRenderer extends tile.Renderer<QuicklookTextureProvider> {
  private filter: RubinImageFilter
  private releaseCallbacks = ReleaseCallbacks()
  private tp: QuicklookTextureProvider

  constructor(
    globe: Globe,
    readonly metadata: QuicklookMetadata,
    filterParams: RubinImageFilterParams,
  ) {
    const filter = new RubinImageFilter(globe.gl, filterParams)
    const tp = new QuicklookTextureProvider(globe, metadata, filter)
    super(globe, tp)
    this.tp = tp
    this.filter = filter
    this.releaseCallbacks.add(() => {
      tp.release()
      filter.release()
    })
  }

  pixelValue(coords: V2) {
    return this.tp.pixelValue(coords)
  }

  release(): void {
    this.releaseCallbacks.flush()
    super.release()
  }

  setFilterParams(filterParams: RubinImageFilterParams, { clearAll, lodBias }: { clearAll?: boolean, lodBias?: number } = {}) {
    const { textureProvider } = this
    const view = this.globe.camera.view()
    const visibleTiles = new Set<string>()
    this.visibleTiles(view, lodBias ?? 0, tileId => visibleTiles.add(tileId))
    this.filter.params = filterParams
    textureProvider.clearCache(tileId => {
      return clearAll || visibleTiles.has(tileId)
    })
    textureProvider.update()
    this.globe.requestRefresh()
  }
}

type PixelInfo = {
  level: number
  value: number
}

class QuicklookTextureProvider extends tile.AsyncTextureProvider {
  private tracts: tile.Tract[]

  constructor(
    globe: Globe,
    readonly metadata: QuicklookMetadata,
    readonly filter: RubinImageFilter,
  ) {
    super(globe)
    this.tracts = [this.mainTract()]
    // @ts-ignore
    const cacheSize: number = this.cache.maxSize
    this.npyCache.setLimit(cacheSize)
  }

  private mainTract() {
    const tract = tile.Tract.fromFitsHeader(this.metadata.wcs)
    // @ts-ignore
    tract.fov = angle.deg2rad(3.5)
    return tract
  }

  private npyCache = new Cache<string, Npy>({ maxSize: 0 })

  walkTracts(cb: (tract: tile.Tract) => void) {
    for (const t of this.tracts) {
      cb(t)
    }
  }

  private getNpyImmediately(level: number, p: number, q: number) {
    const tileId = Tract.encodeTileId(this.tracts[0], level, p, q)
    const npy = this.npyCache.get(tileId)
    if (npy) {
      return npy
    }
  }

  private async getNpy(level: number, p: number, q: number) {
    const npy = this.getNpyImmediately(level, p, q)
    if (npy) {
      return npy
    }
    const tileId = Tract.encodeTileId(this.tracts[0], level, p, q)
    const n = new npyjs()
    const url = `./api/quicklooks/${this.metadata.id}/tiles/${level}/${p}/${q}`
    const fresh = await n.load(url)
    this.npyCache.set(tileId, fresh)
    return fresh
  }

  async makeTileTexture(ref: tile.TileRef, { sync, fadeIn }: { fadeIn: boolean, sync: boolean }) {
    const { level, p, q, tract: { tileSize } } = ref
    const { revision } = this
    const gl = this.globe.gl
    const npy = await this.getNpy(level, p, q)
    const tt = new TileTexture(this, { fadeIn, revision })
    tt.beforeRenderCallback = () => {
      this.getNpyImmediately(level, p, q)
    }
    const { data, dtype, shape } = npy

    if (this.alreadyReleased) {
      return tt
    }

    if (!(dtype === 'float32' && shape.length === 2 && shape[0] === tileSize && shape[1] === tileSize)) {
      console.log({ dtype, shape, tileSize })
      throw new Error(`Unexpected format for (${level}, ${p}, ${q})`)
    }

    this.filter.apply(tt.tex, tileSize, tileSize, 1, t => {
      t.bind(() => {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
        gl.texImage2D(
          gl.TEXTURE_2D,
          0,
          gl.R32F,
          tileSize,
          tileSize,
          0,
          gl.RED,
          gl.FLOAT,
          data,
        )
      })
    })

    tt.bind(() => {
      if (ref.level === ref.tract.maxTileLevel) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
        gl.generateMipmap(gl.TEXTURE_2D)
      }
      if (ref.level === 0) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
      }
    })

    return tt
  }

  pixelValue(coords: V2): PixelInfo {
    const [x, y] = coords
    for (let level = 0; level <= 8; ++level) {
      const q = x >> (8 + level)
      const p = y >> (8 + level)
      const npy = this.getNpyImmediately(level, p, q)
      if (npy) {
        const i = (y >> level) % TILE_SIZE
        const j = (x >> level) % TILE_SIZE
        return {
          level,
          value: npy.data[i * TILE_SIZE + j] as number,
        }
      }
    }
    return {
      level: -1,
      value: Number.NaN,
    }
  }
}


class TileTexture extends tile.TileTexture {
  beforeRenderCallback: (() => void) | undefined

  beforeRender(): void {
    this.beforeRenderCallback?.()
  }
}
