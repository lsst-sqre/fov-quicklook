import { useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe, Layer, path, V3, View } from "@stellar-globe/stellar-globe"
import { useCallback } from "react"

class XyzAxisLayer extends Layer {
  private r: path.Renderer

  constructor(globe: Globe) {
    super(globe)
    this.r = new path.Renderer(globe.gl, {
      blendMode: "NORMAL",
      darkenNarrowLine: false,
      minWidth: 5 * globe.camera.pixelRatio,
    })
    this.onRelease(() => this.r.release())
    this.r.setPaths(
      ([[1, 0, 0], [0, 1, 0], [0, 0, 1]] as V3[]).map(v => ({
        close: false,
        joint: 'NONE',
        points: [
          { color: [...v, 1], size: 0, position: [0, 0, 0], },
          { color: [...v, 1], size: 0, position: v, },
        ],
      }))
    )
  }

  render(view: View): void {
    this.r.render(view)
  }
}

export function XyzLayer$() {
  const factory = useCallback((globe: Globe) => {
    return new XyzAxisLayer(globe)
  }, [])

  const { node } = useLayerBind<XyzAxisLayer>(factory, true)

  return node
}
