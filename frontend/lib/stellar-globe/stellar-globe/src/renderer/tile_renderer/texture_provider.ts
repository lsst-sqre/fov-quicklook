import { vec3 } from 'gl-matrix'
import { Globe } from '~/globe'
import { Cache } from '~/lib/cache'
import { Texture } from '~/lib/gl-wrapper'
import { V3 } from '~/types'
import { loadImage } from '~/utils/image'
import { TileId, Tract } from './tract'
import { waitIdleTime } from '~/utils/time'
import { ReleaseCallbacks } from '~/utils/EventManager'


export abstract class TextureProvider {
  constructor(
    readonly globe: Globe,
  ) {
  }

  protected alreadyReleased = false

  release() {
    this.releaseCallbacks.flush()
    this.alreadyReleased = true
  }

  private releaseCallbacks = ReleaseCallbacks()
  protected onRelease = this.releaseCallbacks.add

  abstract walkTracts(cb: (tract: Tract) => void): void
  abstract get(id: TileId): TileTexture | undefined
  abstract requestTile(id: TileId, options: { immediate: boolean, fadeIn: boolean }): void
  abstract flushQueue(center: V3): void

  private _revision = 0
  public get revision() {
    return this._revision
  }

  update() {
    this._revision++
  }
}


export class TileRef {
  tract: Tract
  level: number
  p: number
  q: number
  center: V3

  constructor(readonly id: TileId) {
    const { tract, level, p, q } = Tract.decodeTileId(id)
    this.tract = tract
    this.level = level
    this.p = p
    this.q = q
    const centerI = ((tract.tileSize << level) * (p + 0.5))
    const centerJ = ((tract.tileSize << level) * (q + 0.5))
    this.center = tract.pixel2xyz(centerJ, centerI)
  }
}

type TileRequest = {
  ref: TileRef
  fadeIn: boolean
}

export abstract class AsyncTextureProvider extends TextureProvider {
  nParallel = 2

  private loading = new Set<TileId>()
  private requestQueue = new Map<TileId, TileRequest>()
  private cache: Cache<TileId, TileTexture>
  private deadTileId = new Set<TileId>()

  constructor(globe: Globe) {
    super(globe)
    this.cache = new Cache({ maxSize: 2000, onDrop: (tt) => tt.release() })
    this.onRelease(() => {
      this.cache.clear()
    })
  }

  get(tileId: TileId) {
    return this.cache.get(tileId)
  }

  requestTile(tileId: TileId, { immediate, fadeIn }: { immediate: boolean, fadeIn: boolean }) {
    if (this.deadTileId.has(tileId)) {
      return
    }
    if (this.loading.has(tileId) || this.requestQueue.has(tileId)) {
      return
    }
    const ref = new TileRef(tileId)
    if (immediate) {
      this.load({ ref, fadeIn }, { sync: immediate })
    }
    else {
      this.requestQueue.set(tileId, { ref, fadeIn })
    }
  }

  flushQueue(center: V3) {
    const rs: TileRequest[] = []
    this.requestQueue.forEach((v) => rs.push(v))
    rs.sort((a, b) => {
      if (a.ref.level !== b.ref.level) {
        return b.ref.level - a.ref.level
      }
      return vec3.sqrDist(a.ref.center, center) - vec3.sqrDist(b.ref.center, center)
    })
    while (rs.length > 0 && this.loading.size < this.nParallel) {
      const r = rs.shift()!
      this.load(r, { sync: false })
    }
    this.requestQueue.clear()
  }

  private async load(r: TileRequest, { sync }: { sync: boolean }) {
    const { ref, fadeIn } = r
    this.loading.add(ref.id)
    if (!sync) {
      await waitIdleTime() // カクつきを軽減
    }
    this.makeTileTexture(ref, { fadeIn, sync }).then(tt => {
      if (this.alreadyReleased) {
        tt.release()
        return
      }
      this.cache.set(ref.id, tt)
      this.globe.requestRefresh()
    }).catch(error => {
      this.deadTileId.add(ref.id)
      console.warn(error)
    }).then(() => {
      this.loading.delete(ref.id)
      if (this.loading.size == 0) {
        this.globe.emit('imageloadend', {})
      }
    })
  }

  protected abstract makeTileTexture(ref: TileRef, options: { fadeIn: boolean, sync: boolean }): Promise<TileTexture>

  clearCache(keep?: (id: TileId) => boolean) {
    if (keep) {
      for (const id of this.cache.keys()) {
        if (!keep(id)) {
          this.cache.delete(id)
          this.deadTileId.delete(id)
        }
      }
    }
    else {
      this.cache.clear()
      this.deadTileId.clear()
    }
  }

  setCacheSize(limit: number) {
    this.cache.setLimit(limit)
  }
}


export abstract class SimpleImageTextureProvider extends AsyncTextureProvider {
  constructor(
    globe: Globe,
  ) {
    super(globe)
  }

  async makeTileTexture(ref: TileRef, { fadeIn }: { fadeIn: boolean }): Promise<TileTexture> {
    const url = this.ref2url(ref)
    const image = await loadImage(url)
    const tt = new TileTexture(this, { fadeIn })
    const gl = this.globe.gl
    tt.bind(() => {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image)
      if (ref.level === ref.tract.maxTileLevel) {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
        gl.generateMipmap(gl.TEXTURE_2D)
      }
    })
    return tt
  }

  abstract ref2url(ref: TileRef): string
}


export class TileTexture {
  readonly revision: number
  readonly tex: Texture
  fadeAlpha = 1

  constructor(readonly tp: TextureProvider, { fadeIn = false, revision }: { fadeIn?: boolean, revision?: number }) {
    const gl = tp.globe.gl
    this.tex = new Texture(gl)
    this.revision = revision ?? tp.revision
    fadeIn && this.fadeIn()
  }

  private fadeIn(duration = 200) {
    this.tp.globe.animations.add((({ r }) => {
      this.fadeAlpha = r
    }), { duration, immediate: true })
  }

  release() {
    this.tex.release()
  }

  bind(cb: () => void) {
    this.tex.bind(cb)
  }

  needUpdate() {
    return this.revision < this.tp.revision
  }

  beforeRender() {
  }
}
