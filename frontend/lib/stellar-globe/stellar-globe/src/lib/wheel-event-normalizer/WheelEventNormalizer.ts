import { realEventDetector } from '.'
import { Inertia } from '~/lib/inertia'

export type PseudoWheelEvent = {
  dt: number
  deltaY: number
  rawEvent: WheelEvent
}

type Options = {
  isRealEvent?: (e: WheelEvent) => boolean
  inertia?: Inertia,
  hotDuration: number
  on: {
    start?: () => void
    end?: () => void
  }
}

const defaultOptions: Partial<Options> = {
  hotDuration: 150,
  on: {},
}

export class WheelEventNormalizer {
  private isRealEvent: (e: WheelEvent) => boolean
  private inertia: Inertia
  private raf?: number
  private direction = 0
  private rawFire?: number
  private options: Options
  lastRawEvent!: WheelEvent

  constructor(
    private cb: (e: PseudoWheelEvent) => void,
    options: Partial<Options> = defaultOptions,
  ) {
    this.options = options = { ...defaultOptions, ...options } as Options
    this.isRealEvent = options.isRealEvent ?? realEventDetector()
    this.inertia = options.inertia ?? new Inertia()
  }

  feedRawEvent(e: WheelEvent) {
    this.lastRawEvent = e
    if (!this.isRealEvent(e)) {
      return
    }
    this.direction = Math.sign(e.deltaY)
    this.rawFire = performance.now()
    if (this.raf === undefined) {
      this.options.on.start?.()
      this.startAnimation()
    }
  }

  private startAnimation() {
    const refresh = (now: number) => {
      this.raf = undefined
      const dt = now - t0
      const hot = now - this.rawFire! < this.options.hotDuration
      t0 = now
      if (hot) {
        this.inertia.addImpulse(dt * this.direction)
      }
      this.inertia.evolve(now)
      const { moving, v } = this.inertia.state
      if (moving || hot) {
        this.cb({ dt, deltaY: v, rawEvent: this.lastRawEvent })
        this.raf = requestAnimationFrame(refresh)
      }
      else {
        this.options.on.end?.()
      }
    }
    let t0 = performance.now()
    this.raf = requestAnimationFrame(refresh)
  }

  stop() {
    this.inertia.stop()
  }
}
