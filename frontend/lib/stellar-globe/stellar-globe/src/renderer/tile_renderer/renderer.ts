import { mat3, vec3 } from 'gl-matrix'
import { Cache } from '~/lib/cache'
import { AttribList, Program, utils as glUtils } from '~/lib/gl-wrapper'
import { TextureProvider, TileTexture } from './texture_provider'
import { TileId, Tract } from './tract'

import { Globe } from '~/globe'
import { square } from '~/utils/math'
import { View } from '~/view'
import shaderFrag from './frag.glsl?raw'
import shaderVert from './vert.glsl?raw'
import { V4 } from '~/types'


export class Renderer<TP extends TextureProvider = TextureProvider> {
  readonly gl: WebGL2RenderingContext
  readonly program: Program
  readonly attribList: AttribList

  animationLod = 1
  lodBias = 0
  integerLevel = false
  alreadyReleased = false
  color: V4 = [1, 1, 1, 1]

  constructor(
    readonly globe: Globe,
    readonly textureProvider: TP,
  ) {
    const { gl } = globe
    this.gl = gl
    this.program = Program.new(
      this.gl,
      shaderVert,
      shaderFrag,
    )
    this.attribList = new AttribList(this.gl, {
      members: [{ name: 'a_coord', nComponents: 2 }],
      array: this.buildArray(),
    })
  }

  release() {
    this.alreadyReleased = true
    this.attribList.release()
    this.program.release()
  }

  render(view: View, alpha = 1) {
    if (alpha <= 0) {
      return
    }
    this.activateProgram(() => {
      this.visibleTracts(view, tract => {
        const { program } = this
        const r = new TractRenderer(this, tract)
        program.uniform1f({ u_layer_alpha: alpha })
        program.uniform4fv({ u_color: this.color })
        program.uniformMatrix4fv({ u_pvMatrix: view.mvp.pv })
        r.render(view)
      })
      this.textureProvider.flushQueue(view.mvp.direction)
    })
  }

  // OPTIMIZE
  private visibleTracts(view: View, cb: (tract: Tract) => void) {
    const fovCenter = view.mvp.direction
    const arc = view.mvp.arc
    this.textureProvider.walkTracts((tract) => {
      if (vec3.sqrDist(fovCenter, tract.refPoint) <= square(arc + tract.fov)) {
        cb(tract)
      }
    })
  }

  /** @internal */
  draw() {
    const { gl } = this
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, this.attribList.vertexCount)
  }

  private activateProgram(cb: () => void) {
    const { gl, program } = this
    program.use()
    this.attribList.enable(this.program, () => {
      glUtils.enable(gl, [gl.BLEND], () => {
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
        gl.activeTexture(gl.TEXTURE0)
        program.uniform1i({ u_texture0: 0 })
        cb()
        gl.bindTexture(gl.TEXTURE_2D, null)
      })
    })
  }

  private buildArray() {
    const a = [0, 0, 1, 0, 0, 1, 1, 1]
    return new Float32Array(a)
  }

  visibleTiles(view: View, lodBias: number, cb: (tileId: TileId) => void) {
    this.visibleTracts(view, tract => {
      const r = new TractRenderer(this, tract)
      const { tiles } = r.visibleTiles(view, lodBias, false)
      for (const tile of tiles) {
        cb(tile.tile.id)
      }
    })
  }
}


type TileAndTexture = {
  tile: Tile
  tt: TileTexture
}


class TractRenderer {
  constructor(
    readonly renderer: Renderer,
    readonly tract: Tract,
  ) {
  }

  render(view: View) {
    const tract = this.tract
    const { lodBias, animationLod } = this.renderer
    const { tiles, baseLevel, lodAlpha } = this.visibleTiles(view, lodBias + animationLod * view.lodBias, true)
    tiles.sort((a, b) => b.tile.level - a.tile.level)
    this.renderer.program.uniformMatrix4fv({ u_mMatrix: tract.mMatrix })
    for (const tile of tiles) {
      const alpha = !this.renderer.integerLevel && baseLevel === tile.tile.level ? lodAlpha : 1
      tile.tile.render(alpha, this.renderer, tile.tt)
    }
  }

  visibleTiles(view: View, lodBias: number, doRequest: boolean) {
    const tract = this.tract
    const tiles: TileAndTexture[] = []
    const done = new Set<TileId>()
    const { minP, maxP, minQ, maxQ, baseLevel, lodAlpha } = tract.tileIndices(view, lodBias)
    for (let p = minP; p <= maxP; ++p) {
      for (let q = minQ; q <= maxQ; ++q) {
        this.readyTilesFor(baseLevel, p, q, doRequest, (tile, tt) => {
          if (!done.has(tile.id)) {
            tiles.push(({ tile, tt }))
          }
          done.add(tile.id)
        })
      }
    }
    return { tiles, baseLevel, lodAlpha }
  }

  private readyTilesFor(baseLevel: number, p: number, q: number, doRequest: boolean, cb: (tile: Tile, tt: TileTexture) => void) {
    const { renderer, tract } = this
    const { textureProvider } = renderer
    for (let level = baseLevel; level <= tract.maxTileLevel; ++level) {
      const id = tract.encodeTileId(level, p, q)
      const tt = textureProvider.get(id)
      const tile = Tile.get(id)
      if (tt) {
        cb(tile, tt)
        doRequest && tt.needUpdate() && textureProvider.requestTile(id, {
          fadeIn: false,
          immediate: level < tract.maxTileLevel
        })
        if ((renderer.integerLevel || level > baseLevel) && tt.fadeAlpha >= 1) {
          break
        }
      } else {
        doRequest && textureProvider.requestTile(id, { immediate: false, fadeIn: true })
      }
      p >>= 1
      q >>= 1
    }
  }
}


class Tile {
  readonly level: number
  readonly texMatrix: mat3
  readonly tileMatrix: mat3
  // readonly a2mMatrix: mat4

  constructor(readonly id: TileId) {
    const { tract, level, p, q } = Tract.decodeTileId(id)
    this.level = level
    const s = tract.tileSize << level
    const U = (Math.min(((tract.naxis2 >> level) - 1) << level, s * (p + 1)) - s * p) / s
    const V = (Math.min(((tract.naxis1 >> level) - 1) << level, s * (q + 1)) - s * q) / s
    this.texMatrix = mat3.fromValues(V, 0, 0, 0, U, 0, 0, 0, 1) // window for texture
    this.tileMatrix = mat3.fromValues(s, 0, 0, 0, s, 0, s * q, s * p, 1)
    // this.a2mMatrix = mat4.mul( // mMatrix * tileMatrix * texMatrix
    //     mat4.create(),
    //     tract.mMatrix,
    //     mat4.fromValues(
    //     V * s, 0, 0, 0,
    //     0, U * s, 0, 0,
    //     0, 0, 1, 0,
    //     q * s, p * s, 0, 1)
    // )
  }

  render(alpha: number, renderer: Renderer, tt: TileTexture) {
    tt.beforeRender()
    const { gl, program } = renderer
    gl.bindTexture(gl.TEXTURE_2D, tt.tex.name)
    program.uniform1f({ u_alpha: alpha * tt.fadeAlpha })
    program.uniformMatrix3fv({ u_texMatrix: this.texMatrix, u_tileMatrix: this.tileMatrix })
    renderer.draw()
  }

  private static cache = new Cache<TileId, Tile>({ maxSize: 10000 })
  static get(id: TileId) {
    const tile = this.cache.get(id)
    if (tile) {
      return tile
    }
    const newTile = new Tile(id)
    this.cache.set(id, newTile)
    return newTile
  }
}
