/**
 * These classes abstract MouseEvent and TouchEvent into one.
 */

export class PointerCoord {
  constructor(
    public x: number,
    public y: number,
  ) { }
  clone() {
    return new PointerCoord(this.x, this.y)
  }
}


export function isTouchEvent(e: MouseEvent | TouchEvent): e is TouchEvent {
  return (window as any).TouchEvent && e instanceof TouchEvent
}

export class SinglePointerEvent {
  constructor(readonly e: MouseEvent | TouchEvent) {
  }

  originalEvent<T>(
    { mouse, touch }: { mouse?: (e: MouseEvent) => T, touch?: (e: TouchEvent) => T },
  ) {
    if (isTouchEvent(this.e)) {
      return touch && touch(this.e)
    } else {
      return mouse && mouse(this.e)
    }
  }

  get clientX(): number {
    if (isTouchEvent(this.e)) {
      return (this.e.type === 'touchend' ? this.e.changedTouches : this.e.touches).item(0)!.clientX
    } else {
      return this.e.clientX
    }
  }

  get clientY(): number {
    if (isTouchEvent(this.e)) {
      return (this.e.type === 'touchend' ? this.e.changedTouches : this.e.touches).item(0)!.clientY
    } else {
      return this.e.clientY
    }
  }

  get clientCoord() {
    return new PointerCoord(this.clientX, this.clientY)
  }

  get timeStamp() {
    return this.e.timeStamp
  }

  static onDown(
    target: HTMLElement,
    cb: (e: SinglePointerEvent) => void,
    // cancel?: (e: SinglePointerEvent) => void,
    capture = false,
  ) {
    const mouse = (e: MouseEvent) => {
      cb(new SinglePointerEvent(e))
    }
    const touch = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        cb(new SinglePointerEvent(e))
      }
      // if (e.touches.length > 1) {
      //   cancel && cancel(new SinglePointerEvent(e))
      // }
    }
    target.addEventListener('mousedown', mouse, { capture, passive: true })
    target.addEventListener('touchstart', touch, { capture, passive: true })
    return () => {
      target.removeEventListener('mousedown', mouse, { capture })
      target.removeEventListener('touchstart', touch, { capture })
    }
  }

  static onMove(target: HTMLElement | Document, cb: (e: SinglePointerEvent) => void, capture = false) {
    const mouse = (e: MouseEvent) => {
      cb(new SinglePointerEvent(e))
    }
    const touch = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        cb(new SinglePointerEvent(e))
      }
    }
    target.addEventListener('mousemove', mouse as any, { capture, passive: true })
    target.addEventListener('touchmove', touch as any, { capture, passive: true })
    return () => {
      target.removeEventListener('mousemove', mouse as any, { capture })
      target.removeEventListener('touchmove', touch as any, { capture })
    }
  }

  static onUp(target: HTMLElement | Document, cb: (e: SinglePointerEvent) => void, useCapture = false) {
    const mouse = (e: MouseEvent) => {
      cb(new SinglePointerEvent(e))
    }
    const touch = (e: TouchEvent) => {
      if (e.touches.length === 0) {
        cb(new SinglePointerEvent(e))
      }
    }
    target.addEventListener('mouseup', mouse as any, useCapture)
    target.addEventListener('touchend', touch as any, useCapture)
    return () => {
      target.removeEventListener('mouseup', mouse as any, useCapture)
      target.removeEventListener('touchend', touch as any, useCapture)
    }
  }

}
