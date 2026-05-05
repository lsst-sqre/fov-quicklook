import { DndContext, useDraggable } from '@dnd-kit/core'
import { DragMoveEvent } from "@dnd-kit/core/dist/types"
import { restrictToWindowEdges } from '@dnd-kit/modifiers'
import { CSSProperties, ReactNode, RefObject, useCallback, useLayoutEffect, useMemo, useRef } from 'react'
import { Origin, PartialSize, Position, Rect, Size } from './types'
import { convertOrigin } from './utils'


type ResizableProps = {
  children: ReactNode
  position: Position | undefined
  setPosition: React.Dispatch<React.SetStateAction<Position | undefined>>
  size: PartialSize | undefined
  setSize: React.Dispatch<React.SetStateAction<PartialSize | undefined>>
  container: RefObject<HTMLElement>
  minSize?: Size
  enabled: { x: boolean, y: boolean }
  origin: Origin
}


const defaultMinSize = { width: 8, height: 8 } as const


export function Resizable(props: ResizableProps) {
  const { enabled } = props
  if (enabled.x || enabled.y) {
    return <EnabledResizable {...props} />
  }
  else {
    return props.children
  }
}


const directions = {
  n: { x: 0, y: -1 },
  e: { x: 1, y: 0 },
  s: { x: 0, y: 1 },
  w: { x: -1, y: 0 },
  ne: { x: 1, y: -1 },
  nw: { x: -1, y: -1 },
  se: { x: 1, y: 1 },
  sw: { x: -1, y: 1 },
} as const

const xy2widthHeight = {
  x: 'width',
  y: 'height',
} as const

type DragState = {
  initialPosition: Rect
  direction: keyof typeof directions
}


function EnabledResizable({
  children,
  container,
  setPosition,
  size,
  setSize,
  minSize = defaultMinSize,
  enabled,
  origin,
}: ResizableProps) {
  // const positionAtDragStart = useRef<(Size & Position) | undefined>(undefined)
  const dragState = useRef<DragState | undefined>()

  const onDragStart = useCallback((e: DragMoveEvent) => {
    const { left, top, width, height } = container.current!.getBoundingClientRect()
    dragState.current = {
      initialPosition: { left, top, width, height },
      direction: e.active.id as DragState['direction']
    }
  }, [container])

  const onDragEnd = useCallback(() => {
    dragState.current = undefined
  }, [])

  const onDragMove = useCallback((e: DragMoveEvent) => {
    const updateSize = (axis: 'x' | 'y', sign: number) => {
      const wh = xy2widthHeight[axis]
      const p0 = dragState.current!.initialPosition
      const newSize = Math.max(minSize[wh], p0[wh] + sign * e.delta[axis])
      setSize(size => {
        return {
          ...(size ?? {}),
          [wh]: newSize,
        }
      })
    }
    const dir = directions[e.active.id as keyof typeof directions]
    dir.x !== 0 && updateSize('x', dir.x)
    dir.y !== 0 && updateSize('y', dir.y)
  }, [minSize, setSize])

  useLayoutEffect(() => {
    // sizeの変更に基づいて位置を調整する。
    // render phaseではminmaxSize適用の結果が得られないので、ここで調整
    if (dragState.current) {
      const p0 = dragState.current.initialPosition
      const rect = container.current!.getBoundingClientRect()
      const { width, height } = rect
      let { left, top } = rect
      let right = window.innerWidth - rect.right
      let bottom = window.innerHeight - rect.bottom
      const dir = directions[dragState.current.direction]
      if (dir.x < 0 && origin.x === 'left') {
        left = p0.left - (width - p0.width)
      }
      if (dir.x > 0 && origin.x === 'right') {
        right = window.innerWidth - (p0.left + p0.width) - (width - p0.width)
      }
      if (dir.y < 0 && origin.y === 'top') {
        top = p0.top - (height - p0.height)
      }
      if (dir.y > 0 && origin.y === 'bottom') {
        bottom = window.innerHeight - (p0.top + p0.height) - (height - p0.height)
      }
      setPosition({
        [origin.x]: origin.x === 'left' ? left : right,
        [origin.y]: origin.y === 'top' ? top : bottom,
      } as Position)
    }
  }, [container, origin, setPosition, size])

  return (
    <DndContext
      onDragStart={onDragStart}
      onDragMove={onDragMove}
      onDragEnd={onDragEnd}
      modifiers={[restrictToWindowEdges]}
    >
      {children}
      {enabled.y && <ResizeHandle n />}
      {enabled.y && enabled.x && <ResizeHandle n e />}
      {enabled.x && <ResizeHandle e />}
      {enabled.x && enabled.y && <ResizeHandle e s />}
      {enabled.y && <ResizeHandle s />}
      {enabled.y && enabled.x && <ResizeHandle s w />}
      {enabled.x && <ResizeHandle w />}
      {enabled.x && enabled.y && <ResizeHandle w n />}
    </DndContext>
  )
}


type Direction = 'n' | 'e' | 'w' | 's'


function ResizeHandle({ n, w, e, s, size = 8 }: Partial<Record<Direction, boolean>> & { size?: number }) {
  const boxPosition = useMemo<CSSProperties>(() => ({
    // backgroundColor: 'rgba(0, 0, 255, 0.25)',
    position: 'absolute',
    left: w ? `${-size}px` : e ? undefined : `${size}px`,
    right: e ? `${-size}px` : w ? undefined : `${size}px`,
    width: (e || w) ? `${2 * size}px` : undefined,
    top: n ? `${-size}px` : s ? undefined : `${size}px`,
    bottom: s ? `${-size}px` : n ? undefined : `${size}px`,
    height: (n || s) ? `${2 * size}px` : undefined,
    cursor: (n && e || s && w) ? 'nesw-resize' :
      (n && w || s && e) ? 'nwse-resize' :
        (n || s) ? 'ns-resize' :
          (e || w) ? 'ew-resize' : undefined,
  }), [e, n, s, size, w])

  const id = n ? (e ? 'ne' : w ? 'nw' : 'n') :
    s ? (e ? 'se' : w ? 'sw' : 's') :
      e ? 'e' : 'w'

  const { setNodeRef, listeners, attributes, } = useDraggable({
    id,
  })

  const style = {
    ...boxPosition,
  }

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes} />
  )
}


// const id = (() => {
//   const map = new Map<unknown, number>()
//   return (obj: unknown) => {
//     if (!map.has(obj)) {
//       map.set(obj, map.size)
//     }
//     return map.get(obj)
//   }
// })()
