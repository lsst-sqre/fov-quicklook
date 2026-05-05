import { Globe } from "~/globe"
import { BlendMode, Path, Renderer } from "~/renderer/path_renderer"
import { View } from "~/view"
import { Layer } from "./layer"
import { overlayAlpha } from "./overlayAlpha"


type PathLayerOptions = {
  paths: Path[]
  blendMode?: BlendMode
  dimOnZoom?: boolean
  darkenNarrowLine?: boolean
}


export class PathLayer extends Layer {
  protected pathRenderer!: Renderer
  private _dimOnZoom: boolean

  constructor(
    globe: Globe,
    _options: PathLayerOptions,
  ) {
    super(globe)
    const options: Required<PathLayerOptions> = { ...PathLayer.defaultOptions(), ..._options }
    this.pathRenderer = new Renderer(this.globe.gl, options)
    this._dimOnZoom = options.dimOnZoom
    this.onRelease(() => {
      this.pathRenderer.release()
    })
    this.pathRenderer.setPaths(_options.paths)
  }

  render(view: View) {
    const alpha = this._dimOnZoom ? overlayAlpha(view) : 1
    this.pathRenderer.render(view, alpha)
  }

  set paths(paths: Path[]) {
    this.pathRenderer.setPaths(paths)
    this.globe.requestRefresh()
  }

  set blendeMode(blendMode: BlendMode) {
    this.pathRenderer.blendMode = blendMode
    this.globe.requestRefresh()
  }

  set dimOnZoom(dimOnZoom: boolean) {
    this._dimOnZoom = dimOnZoom
    this.globe.requestRefresh()
  }

  set darkenNarrowLine(darkenNarrowLine: boolean) {
    this.pathRenderer.darkenNarrowLine = darkenNarrowLine
    this.globe.requestRefresh()
  }

  static defaultOptions() {
    return {
      blendMode: 'NORMAL' as BlendMode,
      dimOnZoom: false,
      darkenNarrowLine: true,
    }
  }
}
