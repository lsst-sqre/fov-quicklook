import { mat4 } from "gl-matrix"
import { Globe } from "~/globe"
import { BlendMode, Path, Renderer } from "~/renderer/path_renderer"
import { V4 } from "~/types"
import { range } from "~/utils/math"
import { View } from "~/view"
import { Layer } from "./layer"
import { overlayAlpha } from "./overlayAlpha"
import { wegblProfile } from "~/devel/webgl-profiler/utils"


function defaultGridOptions() {
  return {
    modelMatrix: undefined as undefined | (() => mat4),
    blendMode: 'ADD' as BlendMode,
    defaultGridColor: [0.25, 0.5, 1, 0.75] as V4,
    width: 0.008,
    thetaLine: {
      nTheta: 18,
      nPhi: 360,
      gridColors: {
        9: [1, 0, 0, 0.75],
      } as { [index: number]: V4 },
    },
    phiLine: {
      nTheta: 180,
      nPhi: 24,
      gridColors: {
        0: [1, 0, 0, 0.5],
        6: [0.5, 1, 0, 0.5],
        12: [0, 1, 1, 0.5],
        18: [0.5, 0, 1, 0.5],
      } as { [index: number]: V4 },
    },
    fadeInDuration: 400,
  }
}


type GridLayerOptions = ReturnType<typeof defaultGridOptions>


export class GridLayer extends Layer {
  protected pathRenderer!: Renderer
  readonly options: GridLayerOptions
  private fadeAlpha = 0

  constructor(
    globe: Globe,
    optionsManipulator?: (draft: GridLayerOptions) => void,
  ) {
    super(globe)
    this.options = defaultGridOptions()
    optionsManipulator?.(this.options)
    this.pathRenderer = new Renderer(this.globe.gl)
    this.pathRenderer.blendMode = this.options.blendMode
    this.pathRenderer.setPaths(this.generatePaths())
    this.onRelease(() => {
      this.pathRenderer.release()
    })
    this.addAnimation(({ r }) => {
      this.fadeAlpha = r
    }, { duration: this.options.fadeInDuration })
  }

  render(view: View) {
    const alpha = this.fadeAlpha * overlayAlpha(view)
    const gl = this.globe.gl
    if (this.options.modelMatrix) {
      this.pathRenderer.modelMatrix = this.options.modelMatrix()
    }
    wegblProfile(gl, 'Grid', () => {
      this.pathRenderer.render(view, alpha)
    })
  }

  private generatePaths() {
    const { width, defaultGridColor } = this.options
    const paths: Path[] = []

    thetaLines: {
      const { nTheta, nPhi, gridColors } = this.options.thetaLine
      for (let i_d = 1; i_d < nTheta; ++i_d) {
        const theta = Math.PI * (i_d / nTheta - 0.5)
        const color: V4 = gridColors[i_d] ?? defaultGridColor
        paths.push({
          points: range(0, nPhi).map((i_a) => {
            const phi = 2 * Math.PI * i_a / nPhi
            return {
              position: [
                Math.cos(theta) * Math.cos(phi),
                Math.cos(theta) * Math.sin(phi),
                Math.sin(theta)
              ],
              color,
              size: width,
            }
          }),
          close: true,
          joint: 'MITER',
        })
      }
    }

    phiLines: {
      const { nTheta, nPhi, gridColors, } = this.options.phiLine
      for (let i_a = 0; i_a < nPhi; ++i_a) {
        const phi = 2 * Math.PI * i_a / nPhi
        const color = gridColors[i_a] ?? defaultGridColor
        paths.push({
          points: range(0, nTheta + 1).map((i_d) => {
            const theta = Math.PI * (i_d - 90) / nTheta
            return {
              position: [
                Math.cos(theta) * Math.cos(phi),
                Math.cos(theta) * Math.sin(phi),
                Math.sin(theta)],
              color,
              size: width,
            }
          }),
          close: false,
          joint: 'MITER',
        })
      }
    }

    return paths
  }
}
