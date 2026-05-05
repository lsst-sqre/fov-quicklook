import { get2dContext } from "./canvas"
import { elementSize } from "./dom"

export function text2imageData(text: string, font = '48pt sans-serif', color = 'rgba(255, 255, 255, 1)', margin = 10) {
  let { width, height } = elementSize((el) => {
    el.style.font = font
    el.innerText = text
  })
  width += 2 * margin
  height += 2 * margin

  return get2dContext(width, height, (ctx) => {
    ctx.font = font
    ctx.textBaseline = 'top'
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    for (const [o, w] of [[0.25, 15], [0.5, 10], [0.75, 5]]) {
      ctx.strokeStyle = `rgba(0, 0, 0, ${o})`
      ctx.lineWidth = w
      ctx.strokeText(text, margin, margin)
    }
    ctx.fillStyle = color
    ctx.fillText(text, margin, margin)
    return ctx.getImageData(0, 0, width, height)
  })
}
