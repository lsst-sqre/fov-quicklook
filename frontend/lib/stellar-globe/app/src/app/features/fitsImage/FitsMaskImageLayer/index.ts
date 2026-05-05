import { Globe, Layer, V4, View, fits, tile } from "@stellar-globe/stellar-globe"
import { FitsMaskTextureProvider } from "./textureProvider"

export type MaskMapMeta = {
  tracts: { [tractName: string]: any }
}


type Options = {
  color: V4
  maskBit: number
  meta: MaskMapMeta
  baseUrl: string
}


export class FitsMaskImageLayer extends Layer {
  private tileRenderer: tile.Renderer<FitsMaskTextureProvider>

  constructor(globe: Globe, readonly options: Options) {
    super(globe)
    this.tileRenderer = new tile.Renderer(this.globe, new FitsMaskTextureProvider(this.globe, options))
    this.tileRenderer.integerLevel = true
    this.tileRenderer.lodBias = 0
    this.tileRenderer.color = options.color
    this.onRelease(() => {
      this.tileRenderer.textureProvider.release()
      this.tileRenderer.release()
    })
  }

  render(view: View): void {
    this.tileRenderer.render(view)
  }

  changeColor(color: V4) {
    this.tileRenderer.color = color
    this.globe.requestRefresh()
  }
}
