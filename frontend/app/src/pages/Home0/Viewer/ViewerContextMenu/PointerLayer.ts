import { useLayerBind } from "@stellar-globe/react-stellar-globe"
import { CursorStyle, Globe, GlobePointerDragEvent, GlobePointerEvent, Layer, makePointingObject } from "@stellar-globe/stellar-globe"
import { useCallback } from "react"


type Callbacks = {
  onDrag?: (e: GlobePointerDragEvent) => void
  onUp?: (e: GlobePointerDragEvent) => void
  onClick?: (e: GlobePointerEvent) => void
  onContextMenu?: (e: GlobePointerEvent) => void
}


class PointerLayer extends Layer {
  constructor(
    globe: Globe,
    { callbacks, cursorStyle }: {
      callbacks: Callbacks,
      cursorStyle: {
        hoverIcon: CursorStyle,
        dragIcon: CursorStyle,
      }
    }
  ) {
    super(globe)
    this.pointingObjects.push(
      makePointingObject({
        hit() {
          return { hit: true }
        },
        hoverIcon: cursorStyle.hoverIcon,
        dragIcon: cursorStyle.dragIcon,
        onPointerDown(downEvent) {
          return {
            onDrag(dragEvent) {
              callbacks.onDrag?.(dragEvent)
            },
            onPointerUp(upEvent) {
              callbacks.onUp?.(upEvent)
            },
          }
        },
        onClick: e => {
          callbacks.onClick?.(e)
        },
        onContextMenu: e => {
          callbacks.onContextMenu?.(e)
        }
      }),
    )
  }
}


type Props = {
  enabled?: boolean
  hoverIcon?: CursorStyle
  dragIcon?: CursorStyle
} & Callbacks


export function PointerLayer$({
  enabled = true,
  onDrag,
  onUp,
  onClick,
  onContextMenu,
  dragIcon = 'default',
  hoverIcon = 'default',
}: Props) {
  const factory = useCallback(
    (globe: Globe) => new PointerLayer(
      globe, {
      callbacks: { onDrag, onUp, onClick, onContextMenu },
      cursorStyle: {
        hoverIcon: hoverIcon,
        dragIcon: dragIcon,
      },
    }),
    [onDrag, onUp, onClick, onContextMenu, hoverIcon, dragIcon],
  )
  const { node } = useLayerBind(factory, enabled)
  return node
}
