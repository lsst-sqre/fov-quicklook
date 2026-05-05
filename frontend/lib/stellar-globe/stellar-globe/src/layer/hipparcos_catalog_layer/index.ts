import { Globe } from "~/globe"
import { Layer } from '~/layer/layer'
import { overlayAlpha } from '~/layer/overlayAlpha'
import { PointRenderer } from "~/renderer/point_renderer"
import { on } from "~/utils/event"
import { setWorkerErrorHandler } from "~/utils/setWorkerErrorHandler"
import { View } from "~/view"
import { RequestMessage, ResponseMessage } from './catalog-loader'
import CatalogWorker from './catalog-loader?worker&inline'
import { wegblProfile } from "~/devel/webgl-profiler/utils"


type Options = {
  fadeInDuration?: number
}


export class HipparcosCatalogLayer extends Layer {
  private pointRenderer: PointRenderer
  private fadeInAlpha = 0

  constructor(
    globe: Globe,
    {
      fadeInDuration = 400,
    }: Options = {}
  ) {
    super(globe)
    this.pointRenderer = new PointRenderer(this.globe.gl)
    this.onRelease(loadCatalog(
      globe.dataRepository,
      () => {
        this.addAnimation(({ r }) => {
          this.fadeInAlpha = r
        }, { duration: fadeInDuration })
      },
      buffer => {
        const array = new Float32Array(buffer)
        this.pointRenderer.setArray(array)
        this.globe.requestRefresh()
      }))
    this.onRelease(() => {
      this.pointRenderer!.release()
    })
  }

  render(view: View) {
    wegblProfile(this.globe.gl, 'HipparcosCatalog', () => {
      const alpha = this.fadeInAlpha * overlayAlpha(view)
      this.pointRenderer?.render(view, alpha)
    })
  }
}


function loadCatalog(dataRepository: string, onFirstLoad: () => void, onLoad: (buffer: ArrayBuffer) => void) {
  const loader = setWorkerErrorHandler(new CatalogWorker())

  let messageCount = 0

  let cleanup: (() => void) | undefined = () => {
    cleanup = undefined
    offLoaderMessage()
    loader.terminate()
  }

  // @ts-ignore
  const offLoaderMessage = on(loader, 'message',
    (e: MessageEvent) => {
      const res: ResponseMessage = e.data
      if (cleanup) {
        if (messageCount++ === 0) {
          onFirstLoad()
        }
        onLoad(res.buffer)
      }
      if (res.end) {
        cleanup?.()
      }
    }
  )

  const request: RequestMessage = {
    dataRepository,
  }

  loader.postMessage(request)

  return () => {
    cleanup?.()
  }
}
