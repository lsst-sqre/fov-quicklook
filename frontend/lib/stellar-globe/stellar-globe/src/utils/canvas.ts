export function get2dContext<T>(width: number, height: number, cb: (ctx: CanvasRenderingContext2D) => T) {
  const { canvas, ctx } = getCanvas()
  canvas.width = width
  canvas.height = height
  ctx.save()
  ctx.clearRect(0, 0, width, height)
  const retval = cb(ctx)
  ctx.restore()
  return retval
}

const getCanvas = (() => {
  let canvas: HTMLCanvasElement
  let ctx: CanvasRenderingContext2D
  return () => {
    canvas ??= document.createElement('canvas')
    ctx ??= canvas.getContext('2d', { willReadFrequently: true })!
    return { canvas, ctx }
  }
})()
