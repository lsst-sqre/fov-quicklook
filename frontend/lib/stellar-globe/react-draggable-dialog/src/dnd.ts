// https://github.com/clauderic/dnd-kit/issues/477#issuecomment-1713536492
import { PointerSensor as LibPointerSensor } from '@dnd-kit/core'
import { PointerEvent } from 'react'

// Block DnD event propagation if element have "data-no-dnd" attribute
const handler = ({ nativeEvent: event }: PointerEvent) => {
  let cur = event.target as HTMLElement

  while (cur) {
    if (cur.dataset && cur.dataset.noDnd) {
      return false
    }
    cur = cur.parentElement as HTMLElement
  }

  return true
}

export class PointerSensor extends LibPointerSensor {
  static activators = [{ eventName: 'onPointerDown', handler }] as typeof LibPointerSensor['activators']
}
