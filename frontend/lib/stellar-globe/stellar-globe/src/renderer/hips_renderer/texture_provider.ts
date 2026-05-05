import * as healpix from '@hscmap/healpix'
import { vec3 } from 'gl-matrix'
import { Globe } from '~/globe/index'
import { Cache } from '~/lib/cache'
import { Texture } from '~/lib/gl-wrapper'
import { V3 } from '~/types'
import { ReleaseCallbacks } from '~/utils/EventManager'
import { loadImage } from '~/utils/image'
import { izenith3 } from '~/utils/matrilx-utils'
import { CoordFrame, HID } from '.'
import { size2order } from './healpix'
import { HiPSProperties, fetchHiPSProperties } from './properties'


export abstract class TextureProvider {
  constructor(
    readonly globe: Globe,
    readonly tileOrder: number,
    readonly maxTileOrder: number,
    readonly minTileOrder: number,
    readonly coordFrame: CoordFrame,
  ) {
  }

  abstract get(hid: HID): TileTexture | undefined
  abstract request(hid: number, options?: { immediate: boolean }): void

  /** @internal */
  abstract flushQueue(center: V3): void

  protected abstract makeTileTexture(ref: TextureRef, fadeIn: boolean): Promise<TileTexture>

  private _revision = 0

  get revision() {
    return this._revision
  }

  update() {
    ++this._revision
  }

  private releaseCallbacks = ReleaseCallbacks()
  protected onRelease = this.releaseCallbacks.add

  release() {
    this.releaseCallbacks.flush()
  }
}

export class TileTexture {
  readonly tex: Texture
  readonly revision: number
  fadeAlpha = 1

  constructor(tp: TextureProvider, fadeIn: boolean) {
    const gl = tp.globe.gl
    this.tex = new Texture(gl)
    this.revision = tp.revision
    if (fadeIn) {
      tp.globe.animations.add((({ r }) => {
        this.fadeAlpha = r
      }), { duration: 200 })
    }
  }

  release() {
    this.tex.release()
  }

  bind(cb: () => void) {
    this.tex.bind(cb)
  }
}


export class TextureRef {
  center: vec3
  readonly order: number
  readonly index: number

  constructor(readonly hid: number) {
    const { order, ipix } = healpix.uniq2orderpix(hid)
    this.order = order
    this.index = ipix
    this.center = healpix.pix2vec_nest(1 << order, ipix) as any
  }
}


export abstract class AsyncTextureProvider extends TextureProvider {
  protected cache = new Cache<HID, TileTexture>({ maxSize: 1000, onDrop: tt => tt.release() })

  private alreadyReleased = false

  release() {
    this.alreadyReleased = true
    this.cache.clear()
    super.release()
  }

  get(hid: number) {
    return this.cache.get(hid)
  }

  private refsToLoad = new Map<HID, TextureRef>() // requestによって追加される
  private refsInLoading = new Map<HID, TextureRef>()
  private deadHid = new Set<HID>()

  request(hid: number, options?: { immediate: boolean }): void {
    const immediate = options?.immediate ?? false
    if (!this.deadHid.has(hid) && !this.refsInLoading.has(hid) && !this.refsToLoad.has(hid)) {
      const ref = new TextureRef(hid)
      if (immediate) {
        this.load(ref)
      }
      else {
        this.refsToLoad.set(hid, ref)
      }
    }
  }

  nParallel = 4

  /** @internal */
  flushQueue(center: V3) {
    if (this.refsInLoading.size >= this.nParallel) {
      return
    }
    const refs: TextureRef[] = []
    this.refsToLoad.forEach((ref) => refs.push(ref))
    refs.sort((a, b) => {
      return a.order !== b.order ? a.order - b.order : vec3.sqrDist(center, a.center) - vec3.sqrDist(center, b.center)
    })
    for (const ref of refs) {
      if (this.refsInLoading.size >= this.nParallel) {
        break
      }
      this.load(ref)
    }
    this.refsToLoad.clear()
  }

  private load(ref: TextureRef) {
    this.refsInLoading.set(ref.hid, ref)
    const fadeIn = !this.cache.has(ref.hid)
    this.makeTileTexture(ref, fadeIn).then((tt) => {
      if (this.alreadyReleased) {
        tt.release()
      } else {
        this.cache.set(ref.hid, tt)
        this.globe.requestRefresh()
      }
    }).catch(error => {
      this.deadHid.add(ref.hid)
      console.error(error)
    }).then(() => {
      this.refsInLoading.delete(ref.hid)
      this.globe.requestRefresh()
    })
  }

  /** @internal */
  clearCacheWithOrderAbove(lowerOrder: number) {
    for (const hid of this.cache.keys()) {
      const { order } = healpix.uniq2orderpix(hid)
      if (order > 0 && order >= lowerOrder) {
        this.cache.delete(hid)
      }
    }
  }
}


export class SimpleImageTextureProvider extends AsyncTextureProvider {
  readonly baseUrl: string
  readonly properties: HiPSProperties
  readonly format: string

  constructor(
    globe: Globe,
    baseUrl: string,
    properties: HiPSProperties,
  ) {
    const hipsOrderLimit = 13
    if (Number(properties.hips_order) > hipsOrderLimit) {
      console.warn(`hips_order exceeded the limit: ${properties.hips_order} > ${hipsOrderLimit}`)
    }
    const maxOrder = Math.min(Number(properties.hips_order), hipsOrderLimit)
    const minOrder = properties.hips_order_min ? Number(properties.hips_order_min) : 3
    const tileSize = Number(properties.hips_tile_width)
    const coordFrame = ((cf: string) => {
      switch (cf) {
        case 'equatorial': return CoordFrame.EQUATORIAL
        case 'galactic': return CoordFrame.GALACTIC
        case 'hsc/zenith': case 'zenith':
          const [a, d, p] = JSON.parse(properties['hsc/zenith'])
          return new CoordFrame(izenith3(a, d, p))
      }
      return CoordFrame.EQUATORIAL
    })(properties.hips_frame)
    const tileOrder = size2order(tileSize)
    const format = ((fs) => {
      const f = fs.split(/\s+/)[0]
      return ({ jpeg: 'jpg' } as { [name: string]: string })[f] || f
    })(properties.hips_tile_format)
    super(globe, tileOrder, maxOrder, minOrder, coordFrame)
    this.baseUrl = baseUrl
    this.properties = properties
    this.format = format
  }

  async makeTileTexture(ref: TextureRef, fadeIn: boolean): Promise<TileTexture> {
    const url = this.tileId2Url(ref.order, ref.index)
    const image = await loadImage(url)
    const tt = new TileTexture(this, fadeIn)
    const gl = this.globe.gl
    tt.bind(() => {
      // void gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1)
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
      // void gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0)
      if (ref.order === this.minTileOrder) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
        gl.generateMipmap(gl.TEXTURE_2D)
      }
    })
    return tt
  }

  protected tileId2Url(order: number, index: number) {
    const dir = Math.floor(index / 10000) * 10000
    return `${this.baseUrl}/Norder${order}/Dir${dir}/Npix${index}.${this.format}`
  }

  static async fromBaseUrl(globe: Globe, baseUrl: string) {
    const properties = await fetchHiPSProperties(baseUrl)
    return new SimpleImageTextureProvider(globe, baseUrl, properties)
  }
}
