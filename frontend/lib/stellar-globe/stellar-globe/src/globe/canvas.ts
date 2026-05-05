import { Globe } from "~/globe"
import { SkyCoord } from "~/lib/angle"
import { canvasPool } from "~/lib/gl-wrapper"

export type ClientCoord = {
  clientX: number
  clientY: number
}


type CanvasOptions = {
  preserveBuffer?: boolean
  jsdomTest?: boolean
  webgl?: 'webgl' | 'webgl2'
}


export class Canvas {
  readonly domElement: HTMLCanvasElement
  readonly gl: WebGL2RenderingContext
  private readonly releaseCanvas: () => void
  private readonly preserveBuffer: boolean

  constructor(
    private globe: Globe,
    options: CanvasOptions = {},
  ) {
    const {
      preserveBuffer = false,
      jsdomTest = false,
      webgl = 'webgl2'
    } = options
    this.preserveBuffer = preserveBuffer

    const { canvas, gl, release: releaseCanvas } = canvasPool.pull({
      // https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/WebGL_best_practices#avoid_alphafalse_which_can_be_expensive
      alpha: true,
      antialias: false,
      stencil: false,
      premultipliedAlpha: false,
      preserveDrawingBuffer: preserveBuffer,
    }, { jsdomTest, webgl })
    this.domElement = canvas
    this.gl = gl
    this.releaseCanvas = releaseCanvas
    canvas.style.backgroundColor = '#000'
    canvas.style.width = canvas.style.height = '100%'
    canvas.style.display = 'block'
  }

  release() {
    this.releaseCanvas()
  }

  resize(retina: boolean) {
    const canvas = this.domElement
    const r = retina ? window.devicePixelRatio : 1
    const w = r * canvas.clientWidth
    const h = r * canvas.clientHeight
    canvas.width = w
    canvas.height = h
    this.gl.viewport(0, 0, w, h)
  }

  setSize(w: number, h: number) {
    const canvas = this.domElement
    canvas.width = w
    canvas.height = h
    this.gl.viewport(0, 0, w, h)
  }

  get aspectRatio() {
    const c = this.domElement
    const a = c.width / c.height
    return isNaN(a) ? 1 : a
  }

  coordFromClientCoord(e: ClientCoord) {
    return SkyCoord.fromXyz(this.xyzFromClientCoord(e))
  }

  xyzFromClientCoord(e: ClientCoord) {
    return this.xyzFromNdc(this.ndcFromClientCoord(e))
  }

  xyzFromOffset(x: number, y: number) {
    return this.xyzFromNdc(this.ndcFromOffset(x, y))
  }

  coordFromOffset(x: number, y: number) {
    return SkyCoord.fromXyz(this.xyzFromOffset(x, y))
  }

  private xyzFromNdc([ndx, ndy]: [number, number]) {
    return this.globe.camera.view().mvp.ndc2sphereXYZ(ndx, ndy, true)
  }

  private ndcFromClientCoord(e: ClientCoord) {
    const clientRect = this.domElement.getBoundingClientRect()
    const [x, y] = [e.clientX - clientRect.left, e.clientY - clientRect.top]
    return this.ndcFromOffset(x, y)
  }

  private ndcFromOffset(x: number, y: number): [number, number] {
    return [
      2 * x / this.domElement.clientWidth - 1,
      1 - 2 * y / this.domElement.clientHeight,
    ]
  }

  get pixelData() {
    if (!this.preserveBuffer) {
      throw new Error('this.offscreen must be true')
    }
    const gl = this.gl
    const w = gl.drawingBufferWidth
    const h = gl.drawingBufferHeight
    const array = new Uint8Array(w * h * 4)
    gl.finish()
    gl.readPixels(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight, gl.RGBA, gl.UNSIGNED_BYTE, array)
    return {
      width: w,
      height: h,
      buffer: array.buffer,
    }
  }
}
