import * as healpix from '@hscmap/healpix'
import { mat3 } from "gl-matrix"
import { ReleaseCallbacks } from '~/utils/EventManager'
import { Globe } from '~/globe/index'
import { Cache } from '~/lib/cache'
import { AttribList, Program, Texture, utils as glUtils } from '~/lib/gl-wrapper'
import { V3 } from '~/types'
import { clip } from "~/utils/math"
import { View } from '~/view/index'
import { CoordFrame } from './coord_frame'
import shaderFrag from './frag.glsl?raw'
import maskShaderFrag from './mask.frag.glsl?raw'
import { hipsQuadCoeff } from "./healpix"
import * as shiftmap from './shiftmap'
import { TextureProvider, TileTexture } from './texture_provider'
import shaderVert from './vert.glsl?raw'

export type HID = number
const MIN_TILE_ORDER = 2

type Options = {
  animationLod?: number
  lodBias?: number
  integerOrder?: boolean
}


export class Renderer<TP extends TextureProvider = TextureProvider> {
  readonly gl: WebGL2RenderingContext
  readonly program: Program
  readonly attribList: AttribList

  animationLod: number
  lodBias: number
  integerOrder: boolean

  private readonly releaseCallbacks = ReleaseCallbacks()
  private readonly onRelease = this.releaseCallbacks.add
  private readonly tileCache: Cache<HID, Tile>
  readonly shiftmapZero: Texture

  constructor(
    readonly globe: Globe,
    readonly textureProvider: TP,
    {
      animationLod = 1,
      lodBias = 0,
      integerOrder = false,
    }: Options = {},
  ) {
    this.animationLod = animationLod
    this.lodBias = lodBias
    this.integerOrder = integerOrder

    const gl = this.gl = this.globe.gl

    this.program = Program.new(
      gl,
      shaderVert,
      this.shaderFrag(),
    )
    this.onRelease(() => this.program.release())

    this.attribList = new AttribList(gl, {
      members: [{ name: 'a_coord', nComponents: 2 }],
      array: this.buildArray(),
    })
    this.onRelease(() => this.attribList.release())

    this.shiftmapZero = new Texture(gl)
    this.shiftmapZero.bind(() => {
      shiftmap.uploadZeroShiftmap(gl)
    })
    this.onRelease(() => this.shiftmapZero.release())

    this.tileCache = new Cache<HID, Tile>({ maxSize: 5000, onDrop: (t) => t.release() })
    this.onRelease(() => this.tileCache.clear())

    this.onRelease(shiftmap.on('hips-shiftmap-worker-start', () => {
      globe.emit('hips-shiftmap-worker-start', {})
    }))

    this.onRelease(shiftmap.on('hips-shiftmap-worker-end', () => {
      globe.emit('hips-shiftmap-worker-end', {})
    }))

    for (let i = MIN_TILE_ORDER; i < 5; ++i) {
      shiftmap.preload(i)
    }

    globe.requestRefresh()
  }

  release() {
    this.releaseCallbacks.flush()
  }

  render(view: View, alpha = 1) {
    this.activateProgram(() => {
      const { gl, program } = this
      program.uniformMatrix4fv({ u_pvMatrix: view.mvp.pv })
      program.uniformMatrix3fv({ u_rotMatrix: this.textureProvider.coordFrame.mat })
      program.uniform1i({ u_shiftmap: 0 })
      program.uniform1i({ u_texture1: 1 })
      const order = this.visibleTiles(view, (rOrder, hid) => {
        let tile = this.tileCache.get(hid)
        if (!tile) {
          tile = new Tile(this, hid)
          this.tileCache.set(hid, tile)
        }
        tile.render(rOrder, alpha)
      })
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, null)
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, null)
      shiftmap.preload(order)
      shiftmap.preload(order + 1)
      gl.activeTexture(gl.TEXTURE0)
    })
    this.textureProvider.flushQueue(this.textureProvider.coordFrame.invert(view.mvp.direction))
  }

  /** @internal */
  draw() {
    const { gl } = this
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, this.attribList.vertexCount)
  }

  private visibleTiles(view: View, cb: (lodAlpha: number, hid: HID) => void) {
    const { maxTileOrder } = this.textureProvider
    let rOrder = this.realOrder(view)
    if (this.integerOrder) {
      rOrder = Math.floor(rOrder)
    }
    const order = Math.ceil(clip(rOrder, MIN_TILE_ORDER, maxTileOrder))
    const nside = 1 << order
    query_disc_inclusive_nest(this.textureProvider.coordFrame, nside, view.mvp.direction, view.mvp.radius,
      (index) => {
        cb(rOrder, healpix.orderpix2uniq(order, index))
      })
    return order
  }

  realOrder(view: View) {
    // healpixの１ピクセルの面積は 4 pi / (12 * 2**order)
    // healpixの平均の一辺の長さは sqrt(pi / (3 * 2**order))
    const { minTileOrder, maxTileOrder, tileOrder } = this.textureProvider
    const arc = view.mvp.arc
    const baseOrder = Math.log(Math.sqrt(Math.PI / 3) * this.globe.gl.drawingBufferHeight / arc) / Math.LN2
    const realOrder = clip(
      baseOrder - tileOrder - (this.lodBias + this.animationLod * view.lodBias),
      minTileOrder, maxTileOrder,
    )
    return realOrder
  }

  protected activateProgram(cb: () => void) {
    const gl = this.gl
    this.program.use()
    this.attribList.enable(this.program, () => {
      glUtils.enable(gl, [gl.BLEND], () => {
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
        cb()
      })
    })
  }

  private buildArray() {
    const a: number[] = []
    const step = 32
    for (let i = 0; i < step; ++i) {
      const y = i / step
      const y2 = (i + 1) / step
      for (let j = 0; j <= step; ++j) {
        const x = j / step
        for (let k = step > 1 && j === 0 ? 2 : 1; k !== 0; --k) {
          a.push(y2, x)
        }
        for (let k = step > 1 && j === step ? 2 : 1; k !== 0; --k) {
          a.push(y, x)
        }
      }
    }
    return new Float32Array(a)
  }

  protected shaderFrag() {
    return shaderFrag
  }
}

function query_disc_inclusive_nest(
  cf: CoordFrame, nside: number, center: V3, radius: number, cb: (index: number) => void,
) {
  center = cf.invert(center)
  if (radius > Math.PI / 2) {
    const n = 12 * nside * nside
    for (let i = 0; i < n; ++i) {
      cb(i)
    }
  } else {
    healpix.query_disc_inclusive_nest(nside, center, radius, cb)
  }
}

class Tile {
  readonly order: number
  readonly index: number
  readonly coeff: { a: Float32Array[], b: Float32Array[] }
  readonly isBeltEnd: boolean
  shiftmap?: Texture

  constructor(readonly renderer: Renderer, readonly hid: HID) {
    const { order, ipix: index } = healpix.uniq2orderpix(hid)
    this.order = order
    this.index = index
    this.coeff = hipsQuadCoeff(order, index)
    this.isBeltEnd = Tile.isBeltEnd(order, index)
    let alive = true
    this.onRelease(() => alive = false)
    if (shiftmap.needShiftMap(order, index)) {
      shiftmap.fetch(order, index, arr => {
        if (alive) {
          const gl = this.renderer.globe.gl
          this.shiftmap = new Texture(gl)
          this.shiftmap.bind(() => {
            const size = shiftmap.size
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, size, size, 0, gl.RGB, gl.UNSIGNED_BYTE, arr)
          })
          this.onRelease(() => {
            this.shiftmap?.release()
          })
        }
      })
    }
  }

  private releaseCallbacks = ReleaseCallbacks()
  protected onRelease = this.releaseCallbacks.add

  release() {
    this.releaseCallbacks.flush()
  }

  render(rOrder: number, alpha: number) {
    const { gl, program } = this.renderer
    program.uniform1f({ u_belt_end: this.isBeltEnd ? 1 : 0 })
    program.uniformMatrix4fv({
      u_ax: this.coeff.a[0],
      u_ay: this.coeff.a[1],
      u_az: this.coeff.a[2],
    })
    if (this.isBeltEnd) {
      program.uniformMatrix4fv({
        u_bx: this.coeff.b[0],
        u_by: this.coeff.b[1],
        u_bz: this.coeff.b[2],
      })
    }
    this.textures(rOrder, (tt, tMatrix, textureAlpha) => {
      const u_alpha = alpha * textureAlpha
      program.uniform1f({ u_alpha })
      program.uniformMatrix3fv({ u_tMatrix: tMatrix })
      gl.activeTexture(gl.TEXTURE1)
      gl.bindTexture(gl.TEXTURE_2D, tt.tex.name)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, (this.shiftmap || this.renderer.shiftmapZero).name)
      this.renderer.draw()
    })
  }

  private static isBeltEnd(order: number, index: number) {
    const nside = 1 << order
    const nside2 = nside * nside
    const f = Math.floor(index / nside2)
    const { x, y } = healpix.bit_decombine(index % nside2)
    return (f < 4 || 8 <= f) && x + y === nside - 1
  }

  private textures(rOrder: number, cb: (tt: TileTexture, tMatrix: mat3, alpha: number) => void) {
    // このTile内でorderの低いtextureを順に探していく
    const tp = this.renderer.textureProvider
    const tMaxOrder = Math.ceil(rOrder)
    let order = this.order
    let index = this.index
    const tMatrix = mat3.create()
    let beta = 1
    while (order >= tp.minTileOrder) {
      if (order <= tMaxOrder) {
        const hid = healpix.orderpix2uniq(order, index)
        const tt = tp.get(hid)
        if (tt) {
          if (tt.revision < this.renderer.textureProvider.revision) {
            tp.request(hid, { immediate: true })
          }
          const alpha = (tMaxOrder === order ? (1 + rOrder - order) : 1) * tt.fadeAlpha
          const invTMatrix = mat3.invert(mat3.create(), tMatrix)!
          cb(tt, invTMatrix, alpha * beta)
          beta *= 1 - alpha
          if (alpha >= 1) {
            break
          }
        } else {
          tp.request(hid)
        }
      }
      mat3.scale(tMatrix, tMatrix, [2, 2])
      mat3.translate(tMatrix, tMatrix, [index & 2 ? -0.5 : 0, index & 1 ? 0 : -0.5])
      --order
      index >>= 2
    }
  }
}

// マスク用
export class MultiplyRenderer extends Renderer {
  protected activateProgram(cb: () => void) {
    const gl = this.gl
    this.program.use()
    this.attribList.enable(this.program, () => {
      glUtils.enable(gl, [gl.BLEND], () => {
        // gl.blendFunc(gl.SRC_ALPHA, gl.ONE)
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
        cb()
      })
    })
  }

  protected shaderFrag(): string {
    return maskShaderFrag
  }
}
