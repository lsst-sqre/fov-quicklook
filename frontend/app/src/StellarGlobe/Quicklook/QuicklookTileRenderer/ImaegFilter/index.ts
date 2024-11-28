import { ImageFilter } from "@stellar-globe/stellar-globe"
import colormapGray from './colormap-Gray.glsl?raw'

// 'optionA.csv': 'magma',
// 'optionB.csv': 'inferno',
// 'optionC.csv': 'plasma',
// 'optionD.csv': 'viridis',
// 'optionE.csv': 'cividis',
// 'optionF.csv': 'rocket',
// 'optionG.csv': 'mako',
// 'optionH.csv': 'turbo',
// 'viridis_map.csv': 'viridis',

import colormapCividis from './viridisLite/colormap/cividis.glsl?raw'
import colormapInferno from './viridisLite/colormap/inferno.glsl?raw'
import colormapMagma from './viridisLite/colormap/magma.glsl?raw'
import colormapMako from './viridisLite/colormap/mako.glsl?raw'
import colormapPlasma from './viridisLite/colormap/plasma.glsl?raw'
import colormapRocket from './viridisLite/colormap/rocket.glsl?raw'
import colormapTurbo from './viridisLite/colormap/turbo.glsl?raw'
import colormapViridis from './viridisLite/colormap/viridis.glsl?raw'

import shaderBase from './frag.glsl?raw'
import scaleArsinh from './scale-Arsinh.glsl?raw'
import scaleLinear from './scale-Linear.glsl?raw'
import { Texture } from "../../../../../../lib/stellar-globe/stellar-globe/types/lib/gl-wrapper"


export type RubinImageFilterParams = {
  min: number
  max: number
  colormap: 'Gray' | 'Viridis' | 'Magma' | 'Inferno' | 'Plasma' | 'Cividis' | 'Rocket' | 'Mako' | 'Turbo'
  scale: 'Linear' | 'Arsinh'
  gamma: number
}


export class RubinImageFilter {
  private filter: BaseFilter

  constructor(
    readonly gl: WebGL2RenderingContext,
    params: RubinImageFilterParams
  ) {
    this.filter = new BaseFilter(gl, params)
  }

  release() {
    this.filter.release()
  }

  set params(params: RubinImageFilterParams) {
    if ((this.filter.params.colormap !== params.colormap) || (this.filter.params.scale !== params.scale)) {
      this.filter.release()
      this.filter = new BaseFilter(this.gl, params)
    }
    this.filter.params = params
  }

  apply(outTexture: Texture, outWidth: number, outHeight: number, nSources: number, setter: (t: Texture, i: number) => void): void {
    return this.filter.apply(outTexture, outWidth, outHeight, nSources, setter)
  }

  static defaultParams(): RubinImageFilterParams {
    return {
      min: 0,
      max: 1000,
      gamma: 0,
      colormap: 'Gray',
      scale: 'Linear',
    }
  }
}


class BaseFilter extends ImageFilter {
  constructor(
    gl: WebGL2RenderingContext,
    public params: RubinImageFilterParams
  ) {
    const colormap = shaders[`colormap${params.colormap}`]
    const scale = shaders[`scale${params.scale}`]
    super(gl, `${shaderBase}\n${colormap}\n${scale}`)
  }

  setUniformParams() {
    this.program.uniform1f({
      u_min: this.params.min,
      u_max: this.params.max,
      u_gamma: this.params.gamma,
    })
  }
}


const shaders = {
  scaleLinear,
  scaleArsinh,
  colormapGray,
  colormapViridis,
  colormapMagma,
  colormapInferno,
  colormapPlasma,
  colormapCividis,
  colormapRocket,
  colormapMako,
  colormapTurbo,
}
