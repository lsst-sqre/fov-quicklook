import { Globe } from "."
import { cameraToCameraMoveEvent } from "./events"

export type Animation = ReturnType<AnimationInternal["wrap"]>

export type AnimationCallback = {
  t: number
  T: number
  dt: number
  r: number
}

type AnimationOptions = {
  duration?: number,
  immediate?: boolean,
  cameraMotion?: boolean,
}

export class AnimationManager {
  private rafId?: number
  private animations: AnimationInternal[] = []

  constructor(
    private globe: Globe,
  ) {
  }

  add(cb: (args: AnimationCallback) => void, options: AnimationOptions = {}) {
    const a = new AnimationInternal(cb, options, () => {
      const i = this.animations.indexOf(a)
      if (i >= 0) {
        this.animations.splice(i, 1)
      }
    })
    if (a.cameraMotion && this.animations.filter((aa) => aa.cameraMotion).length === 0) {
      this.globe.emit('camera-move-start', cameraToCameraMoveEvent(this.globe.camera))
    }
    this.animations.push(a)
    a.promise.finally(() => {
      if (a.cameraMotion && this.animations.filter((aa) => aa.cameraMotion).length === 0) {
        this.globe.emit('camera-move-end', cameraToCameraMoveEvent(this.globe.camera))
      }
    })
    this.tick()
    return a.wrap()
  }

  private tick() {
    if (this.animations.length > 0 && this.rafId === undefined) {
      this.rafId = requestAnimationFrame(() => {
        // requestAnimationFrame の引数をnowとすると t < 0 となることがある。
        const now = performance.now()
        this.rafId = undefined
        let motionAnimation = 0
        for (const a of this.animations.slice()) {
          if (a.cameraMotion) {
            ++motionAnimation
          }
          a.update(now)
          // この行でexpireするanimationもある
          // expireした場合は(microtaskではなく)この行で this.animations からanimationが減る
        }
        this.globe.draw()
        this.tick()
        if (motionAnimation > 0) {
          this.globe.emit('camera-move', cameraToCameraMoveEvent(this.globe.camera))
        }
      })
    }
  }

  get refreshScheduled() {
    return !!this.rafId
  }

  stopCameraMotion() {
    for (const a of this.animations.slice()) {
      if (a.cameraMotion) {
        a.stop()
      }
    }
  }

  clear() {
    while (this.animations.length > 0) {
      this.animations[0].stop()
    }
  }
}


class AnimationInternal {
  private start = performance.now()
  private last = this.start
  private resolve!: () => void
  private reject!: () => void
  readonly cameraMotion: boolean
  readonly promise: Promise<void>

  constructor(
    private cb: (args: AnimationCallback) => void,
    private options: AnimationOptions = {},
    private onStop: () => void,
  ) {
    this.cameraMotion = !!options.cameraMotion
    this.promise = new Promise<void>((resolve, reject) => {
      this.resolve = resolve
      this.reject = reject
    })
    if (this.options.immediate) {
      this.update(performance.now())
    }
  }

  update(now: number) {
    const { duration } = this.options
    const t = now - this.start
    const dt = now - this.last
    this.last = now
    if (duration === undefined) {
      this.cb({ t, T: now, dt, r: NaN })
    } else if (duration === 0) {
      this.cb({ t, T: now, dt, r: 1 })
      this.expire()
    } else {
      const r = t / duration
      this.cb({ t, T: now, dt, r: Math.min(1, r) })
      if (t > duration) {
        this.expire()
      }
    }
  }

  private expire() {
    this.stop()
  }

  stop(raiseError = false) {
    this.onStop()
    if (raiseError) {
      this.reject()
    } else {
      this.resolve()
    }
  }

  wrap() {
    const stop = this.stop.bind(this)
    return Object.assign(this.promise, { stop })
  }
}
