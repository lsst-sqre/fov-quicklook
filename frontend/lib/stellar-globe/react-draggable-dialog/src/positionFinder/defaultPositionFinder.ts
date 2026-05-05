import { Origin, Position, Rect, Size, TopLeft } from "../types"
import { convertOrigin } from "../utils"

type Options = {
  margin?: number
  container?: Rect
  positionHint?: TopLeft
  origin: Origin
}

export function defaultPositionFinder(
  rects: Rect[],
  size: Size,
  options: Options,
): Position {
  const {
    positionHint,
    margin = 8,
    container = defaultContainer(margin),
  } = options

  const isValidPosition = (p: TopLeft) => {
    const { left, top } = p
    const { width, height } = size
    if (
      container.left <= left &&
      container.top <= top &&
      left + width <= container.left + container.width &&
      top + height <= container.top + container.height
    ) {
      const r0: Rect = { left, top, width, height }
      return !rects.some(r => isOverlapping(r0, r, margin))
    }
    return false
  }

  const target = positionHint ?? { left: container.left, top: container.top }
  let minDistance = Number.POSITIVE_INFINITY
  let bestPosition: TopLeft = target

  for (const p of (function* (): Generator<TopLeft> {
    yield target
    for (const r of rects) {
      for (const top of [
        r.top,
        r.top + (r.height + margin),
        r.top - (size.height + margin),
        container.top,
        container.top + container.height - size.height,
      ]) {
        for (const left of [
          r.left,
          r.left + (r.width + margin),
          r.left - (size.width + margin),
          container.left,
          container.left + container.width - size.width,
        ]) {
          yield { top, left }
        }
      }
    }
  })()) {
    if (isValidPosition(p)) {
      const d = distance(p, target)
      if (minDistance > d) {
        minDistance = d
        bestPosition = p
      }
    }
  }

  return convertOrigin(bestPosition, size, options.origin)
}


function distance(a: TopLeft, b: TopLeft): number {
  return (
    (a.left - b.left) ** 2 +
    (a.top - b.top) ** 2
  )
}


function defaultContainer(margin: number): Rect {
  return {
    top: margin,
    left: margin,
    width: window.innerWidth - 2 * margin,
    height: window.innerHeight - 2 * margin,
  }
}


function isOverlapping(a: Rect, b: Rect, margin: number) {
  b = addMargin(b, margin)
  return !(
    b.left + b.width <= a.left ||
    a.left + a.width <= b.left
  ) && !(
    b.top + b.height <= a.top ||
    a.top + a.height <= b.top
  )
}


function addMargin(r: Rect, margin: number): Rect {
  return {
    left: r.left - margin,
    top: r.top - margin,
    width: r.width + 2 * margin,
    height: r.height + 2 * margin,
  }
}
