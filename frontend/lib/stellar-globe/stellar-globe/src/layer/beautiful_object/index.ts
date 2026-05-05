import { mat4 } from "gl-matrix"
import { tile } from "~/index"
import { View } from "~/view"
import { Globe } from '../../globe'
import { Layer } from "../layer"
import { baseAlpha } from '../overlayAlpha'
import { FitsTextureProvider } from "./TextureProvider"
import * as mixerParams from './mixerParams'
import { wegblProfile } from "~/devel/webgl-profiler/utils"


export class BeautifulObjectLayer extends Layer {
  private renderer: tile.Renderer

  constructor(globe: Globe, which: keyof typeof mixerParams) {
    super(globe)

    const tp = new FitsTextureProvider(globe, `${globe.dataRepository}/pretty_picture/${which}`)
    const params = mixerParams[which]
    tp.mixer.beta = params.beta
    tp.mixer.a = params.a
    tp.mixer.b = params.b
    tp.mixer.bias = params.bias
    tp.mixer.mix = mix2mat4(params.mix, params.nFilters)
    tp.mixer.exposure = params.exposure
    tp.mixer.gamma = params.gamma
    tp.mixer.ground = params.ground
    this.onRelease(() => tp.release())

    this.renderer = new tile.Renderer(globe, tp)
  }

  render(view: View): void {
    const alpha = baseAlpha(view)
    const gl = this.globe.gl
    wegblProfile(gl, 'BeautifulObjects', () => {
      this.renderer.render(view, alpha)
    })
  }
}


function mix2mat4(a: number[], n: number) {
  const b = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
  for (let i = 0; i < 3; ++i) {
    for (let j = 0; j < n; ++j) {
      b[4 * j + i] = a[3 * j + i]
    }
  }
  return mat4.fromValues(
    b[0], b[1], b[2], b[3],
    b[4], b[5], b[6], b[7],
    b[8], b[9], b[10], b[11],
    b[12], b[13], b[14], b[15],
  )
}
