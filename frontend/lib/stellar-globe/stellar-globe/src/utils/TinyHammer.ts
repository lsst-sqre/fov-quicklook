/*

Hammer.jsの互換の簡単な実装
Hammer.jsはimportするだけでwindowやdocumentにアクセスするので
Hammer.jsに依存するとnode.jsからstellar-globeの機能が使えなくなってしまう。

次のイベントにだけ対応
* doubletap
* ２回素早く近いポイントをタップしたときに発生するイベント
* tap2
* ２本の指でタップしたときに発生するイベント
* pinchstart
* ピンチジェスチャーが開始したときに発生するイベント
* pinchmove
* ピンチジェスチャーが進行中のときに発生するイベント

see https://hammerjs.github.io

*/



type EventTypes = 'doubletap' | 'tap2' | 'pinchstart' | 'pinchmove'


export class Hammer {
  private callbacks: Record<EventTypes, ((e: HammerEvent) => void)[]>
  private detectors: GestureDetectors

  constructor(readonly el: HTMLElement) {
    this.callbacks = {
      doubletap: [],
      tap2: [],
      pinchstart: [],
      pinchmove: [],
    }
    this.detectors = {
      doubletap: new DoubleTapDetector(this),
      tap2: new TapWith2FingersDetector(this),
      pinch: new PinchEventDetector(this),
    }
  }

  destroy() {
    for (let type in this.detectors) {
      this.detectors[type as keyof GestureDetectors].destroy()
    }
  }

  get<Type extends keyof GestureDetectors>(type: Type): GestureDetectors[Type] {
    return this.detectors[type] as GestureDetectors[Type]
  }

  on<Type extends EventTypes>(type: Type, callback: (e: HammerEvent) => void): () => void {
    this.callbacks[type].push(callback)
    return () => {
      this.callbacks[type] = this.callbacks[type].filter(cb => cb !== callback)
    }
  }

  /** @internal */
  runListeners(e: HammerEvent) {
    for (let cb of this.callbacks[e.type]) {
      cb(e)
    }
  }
}


type HammerEvent = {
  type: EventTypes
  center: { x: number, y: number }
  pointerType: 'touch'
  timeStamp: number
  scale: number
  srcEvent: TouchEvent
}


class GestureDetector {
  protected cleaner = Cleaner()
  protected eventListeners: ((e: HammerEvent) => void)[] = []

  constructor(readonly hammer: Hammer) {
  }

  protected get el() {
    return this.hammer.el
  }

  destroy() {
    this.cleaner.flush()
  }
}


class DoubleTapDetector extends GestureDetector {
  posThreshold: number = 30; // タップ間の最大距離
  timeThreshold: number = 300; // タップ間の最大時間 (ミリ秒)
  lastTap: { timeStamp: number, x: number, y: number } | null = null;

  constructor(hammer: Hammer) {
    super(hammer)
    const off = on(this.el, 'touchstart', (e) => {
      if (e.touches.length === 1) { // シングルタッチのみを処理
        const touch = e.touches[0]
        const currentTime = e.timeStamp
        const currentX = touch.clientX
        const currentY = touch.clientY

        if (this.lastTap && currentTime - this.lastTap.timeStamp < this.timeThreshold) {
          const dx = currentX - this.lastTap.x
          const dy = currentY - this.lastTap.y
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance < this.posThreshold) {
            this.hammer.runListeners({
              type: 'doubletap',
              center: { x: this.lastTap.x, y: this.lastTap.y },
              pointerType: 'touch',
              timeStamp: currentTime,
              scale: 1,
              srcEvent: e,
            })
            this.lastTap = null // ダブルタップをリセット
            e.preventDefault()
            return
          }
        }

        // タップ情報を更新
        this.lastTap = { timeStamp: currentTime, x: currentX, y: currentY }
      }
    })
    this.cleaner.add(off)
  }

  set(options: { posThreshold?: number, timeThreshold?: number }) {
    if (options.posThreshold !== undefined) {
      this.posThreshold = options.posThreshold
    }
    if (options.timeThreshold !== undefined) {
      this.timeThreshold = options.timeThreshold
    }
  }
}


function getTouchCenter(touches: TouchList) {
  let x = 0
  let y = 0
  for (let i = 0; i < touches.length; i++) {
    x += touches[i].clientX
    y += touches[i].clientY
  }
  return {
    x: x / touches.length,
    y: y / touches.length,
  }
}
class TapWith2FingersDetector extends GestureDetector {
  constructor(hammer: Hammer) {
    super(hammer)
    this.setupListeners()
  }

  private setupListeners() {
    let touchStartTime: number = 0
    let startPositions: { x: number, y: number }[] = [] // タッチ開始時の位置を記録する配列
    const touchStartHandler = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        touchStartTime = e.timeStamp
        startPositions = Array.from(e.touches).map(touch => ({ x: touch.clientX, y: touch.clientY }))
      }
    }

    const touchEndHandler = (e: TouchEvent) => {
      if (e.touches.length === 0 && (e.timeStamp - touchStartTime) < 500) {
        const endPositions = Array.from(e.changedTouches).map(touch => ({ x: touch.clientX, y: touch.clientY }))
        const moves = startPositions.map((start, i) => {
          const end = endPositions[i] ?? start // 終了位置がない場合は開始位置を使う
          return Math.sqrt(Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2))
        })
        const maxMove = Math.max(...moves) // 最大の移動距離を求める
        const moveThreshold = 10 // 移動量がこれ以下ならタップとみなす

        if (maxMove <= moveThreshold) {
          // タッチの中心点を計算します。
          const center = getTouchCenter(e.changedTouches)
          // イベントリスナーを実行します。
          this.hammer.runListeners({
            type: 'tap2',
            center: center,
            pointerType: 'touch',
            timeStamp: e.timeStamp,
            scale: 1, // 'tap2'イベントの場合、scaleは常に1です。
            srcEvent: e,
          })
          e.preventDefault() // ブラウザのデフォルトの挙動を防ぎます。
        }
      }
    }

    const offStart = on(this.el, 'touchstart', touchStartHandler)
    const offEnd = on(this.el, 'touchend', touchEndHandler)

    this.cleaner.add(offStart)
    this.cleaner.add(offEnd)
  }
}


class PinchEventDetector extends GestureDetector {
  private initialDistance: number | null = null;
  private initialCenter: { x: number, y: number } | null = null;

  constructor(hammer: Hammer) {
    super(hammer)
    this.setupListeners()
  }

  private setupListeners() {
    const offStart = on(this.el, 'touchstart', (e) => {
      if (e.touches.length === 2) {
        this.initialDistance = getDistance(e.touches[0], e.touches[1])
        this.initialCenter = getTouchCenter(e.touches)
        this.hammer.runListeners({
          type: 'pinchstart',
          center: this.initialCenter,
          pointerType: 'touch',
          timeStamp: e.timeStamp,
          scale: 1,
          srcEvent: e,
        })
        e.preventDefault()
      }
    })

    const offMove = on(this.el, 'touchmove', (e) => {
      if (e.touches.length === 2 && this.initialDistance !== null && this.initialCenter !== null) {
        const currentDistance = getDistance(e.touches[0], e.touches[1])
        const scale = currentDistance / this.initialDistance
        const center = getTouchCenter(e.touches)
        this.hammer.runListeners({
          type: 'pinchmove',
          center: center,
          pointerType: 'touch',
          timeStamp: e.timeStamp,
          scale: scale,
          srcEvent: e,
        })
      }
    })

    const offEnd = on(this.el, 'touchend', (_e) => {
      this.initialDistance = null
      this.initialCenter = null
    })

    this.cleaner.add(offStart)
    this.cleaner.add(offMove)
    this.cleaner.add(offEnd)
  }
}

function getDistance(touch1: Touch, touch2: Touch): number {
  const dx = touch1.clientX - touch2.clientX
  const dy = touch1.clientY - touch2.clientY
  return Math.sqrt(dx * dx + dy * dy)
}



type GestureDetectors = {
  doubletap: DoubleTapDetector
  tap2: TapWith2FingersDetector
  pinch: PinchEventDetector
}


function on<K extends keyof GlobalEventHandlersEventMap>(
  target: HTMLElement,
  type: K,
  callback: (this: HTMLElement, ev: GlobalEventHandlersEventMap[K]) => any,
  options?: AddEventListenerOptions,
): () => void {
  target.addEventListener(type, callback as EventListener, options)
  return () => {
    target.removeEventListener(type, callback as EventListener)
  }
}


function Cleaner() {
  const callbacks: (() => void)[] = []

  return {
    add: (cb: () => void) => {
      callbacks.push(cb)
    },
    flush: () => {
      while (callbacks.length > 0) {
        callbacks.pop()!()
      }
    },
  }
}


export default Hammer
