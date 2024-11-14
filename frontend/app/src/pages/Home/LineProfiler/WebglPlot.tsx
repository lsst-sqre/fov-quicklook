import { useEffect, useRef } from "react"
import { WebglLine, ColorRGBA, WebglPlot } from "webgl-plot"


export type WebglPlotProps = {
  xy: Float32Array
  min: number
  max: number
  // x0, y0, x1, y1, x2, y2, ...
  // という順番でxy座標を格納したFloat32Array
}

export function WebglPlotComponent({ xy, min, max }: WebglPlotProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  type WebglPlotContext = {
    wglp: WebglPlot
    line?: WebglLine
  }
  const ctxRef = useRef<WebglPlotContext>()

  useEffect(() => {
    const devicePixelRatio = window.devicePixelRatio || 1
    const canvas = canvasRef.current!
    canvas.width = canvas.clientWidth * devicePixelRatio
    canvas.height = canvas.clientHeight * devicePixelRatio

    const wglp = new WebglPlot(canvas)
    ctxRef.current = { wglp }
  }, [])

  useEffect(
    () => {
      const ctx = ctxRef.current
      if (ctx) {
        const { wglp } = ctx
        const n = xy.length >> 1
        wglp.removeAllLines()
        const color = new ColorRGBA(0, 1, 0, 1)
        const line = new WebglLine(color, n)
        wglp.addLine(line)
        ctx.line = line
        line.scaleX = 2 / n
        line.offsetX = -1
      }
    }, [xy.length])

  useEffect(() => {
    const ctx = ctxRef.current
    if (ctx) {
      const { wglp, line } = ctx
      line!.xy.set(xy)
      // line!.scaleY = 2 / (max - min)
      // line!.offsetY = -min / (max - min) * 2 - 1
      const margin = (max - min) * 0.1
      line!.scaleY = 2 / (max - min + 2 * margin)
      line!.offsetY = -(min - margin) / (max - min + 2 * margin) * 2 - 1
      wglp.update()
    }
  }, [xy, min, max])

  return (
    <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
  )
}

export { WebglPlotComponent as WebglPlot }