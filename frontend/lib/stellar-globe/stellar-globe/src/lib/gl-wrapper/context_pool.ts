import { Dummy } from "~/utils/dummy_class"
import { nonNull } from "./utils"


export function pull(
  options: WebGLContextAttributes,
  {
    jsdomTest,
    webgl,
  }: { jsdomTest: boolean, webgl: 'webgl' | 'webgl2' },
) {
  const canvas = createCanvas()
  const gl: WebGL2RenderingContext = jsdomTest ? (new Dummy() as any) : nonNull(canvas.getContext(webgl, options))
  const release = () => {
    gl.getExtension("WEBGL_lose_context")?.loseContext()
  }
  return { canvas, gl, release }
}


function createCanvas() {
  const canvas = document.createElement('canvas')
  return canvas
}
