import { makePureLayerComponent } from '@stellar-globe/react-stellar-globe'
import { Globe, Layer, SkyCoord, V4, View, angle, glMatrix, path } from '@stellar-globe/stellar-globe'
import { RingsTract } from './RingsTract'
const { mat4 } = glMatrix


class Renderer extends path.Renderer {
  private ringsTract = RingsTract.numRings(120)

  constructor(gl: WebGL2RenderingContext, showPatch: boolean) {
    super(gl)
    const pixelScale = 0.168 // arcsec / pixel
    const tractSize = 36000 // in pixels
    const size = 0.5 * tractSize * angle.deg2rad(pixelScale / 3600)
    this.refreshArray(size, showPatch)
  }

  render(view: View) {
    const { a, d } = SkyCoord.fromXyz(view.mvp.fovCenter)
    const numTractsX = 3
    const numTractsY = 3
    this.ringsTract.tractCenters(a.rad, d.rad, numTractsX, numTractsY, (aa, dd) => {
      this.modelMatrix = modelMatrix(aa, -dd)
      super.render(view)
    })
  }

  private refreshArray(size: number, showPatch: boolean) {
    this.darkenNarrowLine = false
    this.minWidth = 3
    const s = size
    const w = 0.
    const tractColor: V4 = [0, 1, 0, 0.5]
    const patchColor: V4 = [0, 1, 1, 0.25]
    const paths: path.Path[] = []
    paths.push(
      {
        points: [
          { position: [1, -s, -s], color: tractColor, size: w },
          { position: [1, -s, +s], color: tractColor, size: w },
          { position: [1, +s, +s], color: tractColor, size: w },
          { position: [1, +s, -s], color: tractColor, size: w },
        ],
        close: true,
        joint: 'MITER',
      },
    )
    if (showPatch) {
      for (let i = 1; i < 9; ++i) {
        const t = 2 * s * (-0.5 + (i / 9))
        paths.push({
          points: [
            { position: [1, t, -s], color: patchColor, size: w },
            { position: [1, t, +s], color: patchColor, size: w },
          ],
          close: false,
          joint: 'NONE',
        })
        paths.push({
          points: [
            { position: [1, -s, t], color: patchColor, size: w },
            { position: [1, +s, t], color: patchColor, size: w },
          ],
          close: false,
          joint: 'NONE',
        })
      }
    }
    this.setPaths(paths)
  }
}


function modelMatrix(a: number, d: number) {
  const cA = Math.cos(a)
  const sA = Math.sin(a)
  const cD = Math.cos(d)
  const sD = Math.sin(d)
  return mat4.fromValues(
    cA * cD, cD * sA, -sD, 0,
    -sA, cA, 0, 0,
    cA * sD, sA * sD, cD, 0,
    0, 0, 0, 1)
}


class TractFrameLayer extends Layer {
  private renderer: Renderer

  constructor(globe: Globe, showPatch: boolean) {
    super(globe)
    this.renderer = new Renderer(globe.gl, showPatch)
    this.onRelease(() => this.renderer.release())
  }

  render(view: View) {
    this.renderer.render(view)
  }
}


type Props = {
  showPatch: boolean
  visible?: boolean
}


export const TractFrameLayer$ = makePureLayerComponent<Props>(
  (globe, { showPatch }) => new TractFrameLayer(globe, showPatch),
  'visible',
)
