import { Globe } from "~/globe"
import { GlobePointerDragEvent, GlobePointerEvent } from "~/layer/GlobePointerEvent"
import { ReleaseCallbacks } from "~/utils/EventManager"
import { SinglePointerEvent } from "~/utils/SinglePointerEvent"
import { isClick, on } from "~/utils/event"
import { PointingObject } from ".."



export function PointerEventManager(
  globe: Globe,
) {
  const releaseCallbacks = ReleaseCallbacks()
  const domElement = globe.containerElement
  let pointerPressed = false
  const view = () => globe.camera.view()

  const offDown = SinglePointerEvent.onDown(domElement, downSe => {
    // マウス押下中・・・
    const activeObjects: PointingObject[] = []
    const downGe = new GlobePointerEvent(downSe, globe, view())
    pointerPressed = true

    layerLoop:
    for (let i = globe.layers.length - 1; i >= 0; --i) {
      const layer = globe.layers[i]
      for (const object of layer.pointingObjects) {
        const { hit, passThrough } = object.hit(downGe)
        if (hit) {
          globe.setCursor(object.dragIcon(downGe))
          activeObjects.push(object)
          object.runOnPointerDown(downGe)
          if (!passThrough || downGe.stopped) {
            break layerLoop
          }
        }
      }
    }

    const offDrag = SinglePointerEvent.onMove(document, moveEvent => {
      const v = view()
      const delay = moveEvent.timeStamp - downGe.timeStamp
      const moveGe = new GlobePointerEvent(moveEvent, globe, v)
      const dragEvent = new GlobePointerDragEvent(moveGe, downGe)
      for (const o of activeObjects) {
        if (delay >= o.dragDetectionDelay) {
          o.runOnDrag(dragEvent)
        }
      }
    })

    const offUp = SinglePointerEvent.onUp(document, upSe => {
      offUp()
      offDrag()
      pointerPressed = false
      const v = view()
      const upGe = new GlobePointerEvent(upSe, globe, v)
      const dragGe = new GlobePointerDragEvent(upGe, downGe)
      const dragGe0 = new GlobePointerDragEvent(downGe, downGe)
      const upGe0 = new GlobePointerEvent(downSe, globe, v)
      const delay = upSe.timeStamp - downSe.timeStamp
      for (const o of activeObjects) {
        o.runOnPointerUp(delay >= o.dragDetectionDelay ? dragGe : dragGe0)
      }
      if (isClick(downSe, upSe)) {
        for (const o of activeObjects) {
          o.runOnClick(delay >= o.dragDetectionDelay ? upGe : upGe0)
          if (upGe.stopped) {
            break
          }
        }
      }
      checkHover(upGe)
      globe.emit('pointer-up', upGe)
    })

    globe.emit('pointer-down', downGe)
    // マウス押下中おわり
  })
  releaseCallbacks.add(offDown)


  const checkHover = (e: GlobePointerEvent) => {
    if (!pointerPressed) {
      let hitCount = 0
      for (let i = globe.layers.length - 1; i >= 0; --i) {
        const l = globe.layers[i]
        for (const m of l.pointingObjects) {
          const { hit } = m.runHover(e)
          if (hit) {
            if (hitCount++ === 0) {
              globe.setCursor(m.hoverIcon(e))
            }
          }
        }
      }
    }
  }
  let lastMoveEvent: GlobePointerEvent | undefined

  const offMove = SinglePointerEvent.onMove(domElement, (se: SinglePointerEvent) => {
    globe.emit('pointer-move', new GlobePointerEvent(se, globe, view()))
    const e = new GlobePointerEvent(se, globe, view())
    checkHover(e)
    lastMoveEvent = e
  })
  releaseCallbacks.add(offMove)

  releaseCallbacks.add(globe.on('layer-change', () => {
    // レイヤーが追加された時に、マウスオーバーの強調表示などを適用
    lastMoveEvent && checkHover(lastMoveEvent)
  }))

  const offContextMenu = on(domElement, 'contextmenu', e => {
    const se = new SinglePointerEvent(e)
    const ge = new GlobePointerEvent(se, globe, view())
    layerLoop:
    for (let i = globe.layers.length - 1; i >= 0; --i) {
      const layer = globe.layers[i]
      for (const object of layer.pointingObjects) {
        const { hit, passThrough } = object.hit(ge)
        if (hit) {
          object.runOnContextMenu(ge)
          if (!passThrough || ge.stopped) {
            break layerLoop
          }
        }
      }
    }
  })
  releaseCallbacks.add(offContextMenu)

  return releaseCallbacks.flush
}
