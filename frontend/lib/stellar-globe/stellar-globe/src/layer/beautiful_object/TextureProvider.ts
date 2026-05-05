import { mat4 } from "gl-matrix"
import { tile } from "~/index"
import { Fits } from "~/lib/fits"
import { assert } from "~/utils/debug"
import { ImageFilter } from "~/utils/image_filter"
import { Globe } from '../../globe'
import mixerFragShader from './mixer.frag.glsl?raw'


export class FitsTextureProvider extends tile.AsyncTextureProvider {
  readonly mixer: Mixer
  meta?: Meta
  nFilters = -1

  constructor(globe: Globe, readonly url: string, readonly onload?: () => void) {
    super(globe)
    this.mixer = new Mixer(this.globe.gl)
    try {
      this.globe.gl.getExtension('OES_texture_float')
    } catch (error) {
      console.warn(`not supported: OES_texture_float`)
      throw error
    }
    this.loadMetadata()
  }

  release() {
    this.mixer.release()
    super.release()
  }

  private tract?: tile.Tract

  private async loadMetadata() {
    const meta: Meta = await (await fetch(`${this.url}/meta.json`)).json()
    this.meta = meta
    this.tract = tile.Tract.fromFitsHeader(meta.wcs, meta.tractOptions)
    this.nFilters = meta.filters.length
    assert(this.nFilters <= 4, `nFilters <= 4: (${this.nFilters})`)
    this.onload && this.onload()
  }

  walkTracts(cb: (tract: tile.Tract) => void) {
    if (this.tract) {
      cb(this.tract)
    }
  }

  async makeTileTexture(ref: tile.TileRef, { fadeIn, sync }: { fadeIn: boolean, sync: boolean }) {
    const filters = this.meta!.filters
    const urls = filters.map((f) => `${this.url}/${f}/${ref.level}/${ref.p}/${ref.q}.fits`)
    const hdus = await Promise.all(urls.map(async (url) => {
      const hdul =
        await Fits.fetch(url, [{ outputDataType: Fits.DataType.float32, sourceIndex: 0 }]).catch(() => undefined)
      return hdul && hdul[0]
    }))
    const tt = new tile.TileTexture(this, { fadeIn })

    if (!sync) {
      // await waitIdleTime()
    }

    if (this.alreadyReleased) {
      return tt
    }

    const gl = this.globe.gl
    const { tileSize } = ref.tract

    try { // TODO: remove
      this.mixer.apply(tt.tex, tileSize, tileSize, 4, (t, i) => {
        t.bind(() => {
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST)
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST)
          if (i < this.nFilters && hdus[i]) {
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, tileSize, tileSize, 0, gl.RED, gl.FLOAT, hdus[i]!.float32array())
          } else {
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, 1, 1, 0, gl.RED, gl.FLOAT, new Float32Array([0]))
          }
        })
      })
    } catch (e) {
      console.error(e)
    }

    tt.tex.bind(() => {
      if (ref.level === ref.tract.maxTileLevel) {
        gl.generateMipmap(gl.TEXTURE_2D)
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
      }
    })

    return tt
  }
}


class Mixer extends ImageFilter {
  a = [1, 1, 1, 1]
  b = [0, 0, 0, 0]
  beta = [1, 1, 1, 1]
  bias = [0, 0, 0, 0]
  mix = mat4.create()
  exposure = 1
  gamma = 1
  ground = 0

  constructor(
    gl: WebGL2RenderingContext,
  ) {
    super(gl, mixerFragShader)
  }

  setUniformParams() {
    this.program.uniform4fv({
      u_a: this.a,
      u_b: this.b,
      u_beta: this.beta,
      u_bias: this.bias,
    })
    this.program.uniformMatrix4fv({
      // @ts-ignore
      u_mix: this.mix,
    })
    this.program.uniform1f({
      u_exposure: this.exposure,
      u_gamma: this.gamma,
      u_ground: this.ground,
    })
  }
}


type Meta = {
  wcs: {},
  filters: string[],
  tractOptions?: Partial<{
    flipV: boolean,
    minTileLevel: number,
    maxTileLevel: number,
    tileSize: number,
  }>
}