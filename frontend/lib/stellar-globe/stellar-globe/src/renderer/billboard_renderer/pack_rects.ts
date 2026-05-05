export class PackRectSizeError extends Error {
}
export type Box = {
  width: number
  height: number
}
type Position = {
  x: number
  y: number
}
type PackResult = {
  boxPositions: Position[]
  containerWidth: number
  containerHeight: number
}
export function packRects(boxes: Box[], maxWidth: number, maxHeight: number): PackResult {
  const sortedBoxes = boxes.map((box, index) => ({ box, index })).sort((a, b) => b.box.height - a.box.height)

  let tempPositions: (Position & { index: number })[] = []
  let containerWidth = 0
  let containerHeight = 0
  let currentX = 0
  let currentY = 0
  let rowHeight = 0

  for (const { box, index } of sortedBoxes) {
    if (box.width > maxWidth || box.height > maxHeight) {
      throw new PackRectSizeError()
    }

    if (currentX + box.width <= maxWidth) {
      tempPositions.push({ x: currentX, y: currentY, index })
      currentX += box.width
      rowHeight = Math.max(rowHeight, box.height)
    } else {
      currentX = 0
      currentY += rowHeight
      rowHeight = box.height

      tempPositions.push({ x: currentX, y: currentY, index })
      currentX += box.width
    }

    containerWidth = Math.max(containerWidth, currentX)
    containerHeight = currentY + rowHeight

    if (containerHeight > maxHeight) {
      throw new PackRectSizeError()
    }
  }

  const boxPositions = tempPositions.sort((a, b) => a.index - b.index).map(pos => ({ x: pos.x, y: pos.y }))

  return {
    boxPositions,
    containerWidth,
    containerHeight,
  }
}

export function tryPackRects(boxes: Box[], maxSize: number) {
  let size = 256
  while (size < maxSize) {
    try {
      return packRects(boxes, size, size)
    } catch (e) {
      if (e instanceof PackRectSizeError) {
        size *= 2
      }
      else {
        throw e
      }
    }
  }
  throw new PackRectSizeError()
}
