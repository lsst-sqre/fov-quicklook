import { Globe } from "~/globe"
import { Layer } from "~/layer/layer"
import { overlayAlpha } from "~/layer/overlayAlpha"
import { View } from "~/view"
import { fetchHiPSProperties } from "."
import { MultiplyRenderer, Renderer } from "./renderer"
import { SimpleImageTextureProvider } from "./texture_provider"


type RendererOptions = NonNullable<ConstructorParameters<typeof Renderer>[2]>
type SimpleImageLayerOptions = {
  fadeOnZoom?: boolean
  mode?: 'default' | 'multiply'
}


export class SimpleImageLayer extends Layer {
  private renderer?: Renderer
  alpha = 1

  constructor(
    readonly globe: Globe,
    readonly baseUrl: string,
    rendererOptions: RendererOptions = {},
    readonly layerOptions: SimpleImageLayerOptions = {},
  ) {
    super(globe)
    this.asyncInit(rendererOptions)
  }

  private async asyncInit(rendererOptions: RendererOptions) {
    let alive = true
    this.onRelease(() => alive = false)
    const properties = await fetchHiPSProperties(this.baseUrl)
    if (alive) {
      const textureProvider = new SimpleImageTextureProvider(this.globe, this.baseUrl, properties)
      this.renderer = ((mode) => {
        switch (mode) {
          case 'default':
            return new Renderer(this.globe, textureProvider, rendererOptions)
          case "multiply":
            return new MultiplyRenderer(this.globe, textureProvider, rendererOptions)
        }
      })(this.layerOptions.mode ?? 'default')
      this.onRelease(() => {
        this.renderer!.release()
      })
    }
  }

  render(view: View) {
    const alpha = this.alpha * (this.layerOptions.fadeOnZoom ? overlayAlpha(view) : 1)
    if (alpha > 0) {
      this.renderer?.render(view, alpha)
    }
  }
}
