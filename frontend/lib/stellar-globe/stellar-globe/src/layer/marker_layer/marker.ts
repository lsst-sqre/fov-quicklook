import { memoize } from "~/utils/memoize"

type MarkerOptions = {
  width: number
  size: number
}


function reset({ size }: MarkerOptions, { canvas, ctx }: { canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D }) {
  canvas.width = size
  canvas.height = size
  ctx.strokeStyle = '#ffffff'
  ctx.globalAlpha = 1
  ctx.setTransform(size / 2, 0, 0, size / 2, (size - 2) / 2, (size - 2) / 2)
  // ctx.setTransform(size / 2, 0, 0, size / 2, size / 2, size / 2)
  ctx.clearRect(-1, -1, 2, 2)
}

function circle({ width }: MarkerOptions, ctx: CanvasRenderingContext2D) {
  ctx.lineWidth = width
  ctx.beginPath()
  // ctx.arc(0, 0, 1 - ctx.lineWidth, 0, 2 * Math.PI, false)
  ctx.arc(0, 0, 1 - width, 0, 2 * Math.PI, false)
  ctx.stroke()
}

function plus({ width }: MarkerOptions, ctx: CanvasRenderingContext2D) {
  ctx.lineWidth = width
  ctx.beginPath()
  ctx.moveTo(-1, 0)
  ctx.lineTo(+1, 0)
  ctx.moveTo(0, -1)
  ctx.lineTo(0, 1)
  ctx.stroke()
}

function x(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  ctx.rotate(Math.PI / 4)
  plus(options, ctx)
}

function hollowPlus(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  plus(options, ctx)
  ctx.clearRect(-0.5, -0.5, 1, 1)
}

function hollowX(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  ctx.rotate(Math.PI / 4)
  hollowPlus(options, ctx)
}

function dot({ width }: MarkerOptions, ctx: CanvasRenderingContext2D) {
  ctx.lineWidth = width
  ctx.beginPath()
  ctx.arc(0, 0, width / 2, 0, 2 * Math.PI, false)
  ctx.stroke()
}

function circledHollowPlus(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  circle(options, ctx)
  hollowPlus(options, ctx)
}

function circledHollowX(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  circle(options, ctx)
  hollowX(options, ctx)
}

function asterisk(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  plus(options, ctx)
  x(options, ctx)
}

function hollowAsterisk(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  hollowPlus(options, ctx)
  hollowX(options, ctx)
}

function circledHollowAsterisk(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  hollowPlus(options, ctx)
  hollowX(options, ctx)
  circle(options, ctx)
}

function regularPolygon({ width }: MarkerOptions, ctx: CanvasRenderingContext2D, n: number, offset = 0) {
  const s = 1 - width
  ctx.lineWidth = width
  ctx.beginPath()
  ctx.moveTo(s * Math.cos(offset), s * Math.sin(offset))
  for (let i = 0; i < n; ++i) {
    ctx.lineTo(
      s * Math.cos(2 * Math.PI * i / n + offset),
      s * Math.sin(2 * Math.PI * i / n + offset),
    )
  }
  ctx.closePath()
  ctx.stroke()
}

function triangle(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  regularPolygon(options, ctx, 3, -Math.PI / 2)
}

function pentagon(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  regularPolygon(options, ctx, 5, -Math.PI / 2)
}

function square(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  regularPolygon(options, ctx, 4, Math.PI / 4)
}

function diamond(options: MarkerOptions, ctx: CanvasRenderingContext2D) {
  regularPolygon(options, ctx, 4)
}

const markerMakers = {
  circle,
  plus,
  x,
  hollowPlus,
  hollowX,
  dot,
  circledHollowPlus,
  circledHollowX,
  diamond,
  square,
  asterisk,
  hollowAsterisk,
  circledHollowAsterisk,
  triangle,
  pentagon,
} as const


export type MarkerType = keyof typeof markerMakers
export const markerTypes = Object.keys(markerMakers) as MarkerType[]


export const makeMarkerImageData = memoize((type: MarkerType, options: MarkerOptions) => {
  const { size } = options
  const { canvas, ctx } = getCanvas()
  reset(options, { canvas, ctx })
  markerMakers[type](options, ctx)
  return ctx.getImageData(0, 0, size, size)
})


const getCanvas = (() => {
  type Cache = {
    canvas: HTMLCanvasElement
    ctx: CanvasRenderingContext2D
  }
  let cache: Cache | undefined = undefined
  return () => {
    if (!cache) {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d', { willReadFrequently: true })!
      cache = { canvas, ctx }
    }
    return cache
  }
})()
