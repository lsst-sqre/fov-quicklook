type Options = {
  omega0: number // Spring constant
  gamma: number // Drag coefficient
  gamma0: number // Drag coefficient when released
  minSpeed: number
}


const defaultOptions: Options = {
  omega0: 0.05,
  gamma: 0.05,
  gamma0: 0.002,
  minSpeed: 1 / 1000,
}


export class Inertia {
  private h = 0 // hook position
  private x = 0 // position
  private v = 0 // velocity
  private hold = false
  private options: Options
  private t0?: number

  constructor(options: Partial<Options> = {}) {
    this.options = { ...defaultOptions, ...options }
  }

  setOptions(options: Partial<Options>) {
    this.options = { ...this.options, ...options }
    return this
  }

  release() {
    this.hold = false
    return this
  }

  drag(dh: number) {
    this.hold = true
    this.h += dh
    return this
  }

  dragTo(h: number) {
    this.hold = true
    this.h = h
    return this
  }

  addImpulse(impulse: number) {
    this.v += impulse
  }

  stop() {
    this.v = 0
    this.h = this.x
    return this
  }

  reset() {
    this.h = 0
    this.x = 0
    this.v = 0
    return this
  }

  evolve(t: number) {
    if (this.t0 === undefined) {
      this.t0 = t
    }
    const dt = t - this.t0
    this.t0 = t
    const w0 = this.options.omega0
    const g = this.options.gamma
    if (this.hold) {
      const x0 = this.x - this.h
      const v0 = this.v
      if (Math.abs(w0 / g - 1) <= 1.e-3) { // critical damping
        // x(t) = exp(-g * t) * (A * t + B) + h
        // A = g * x0 + v0
        // B = x0
        const A = g * x0 + v0
        const B = x0
        const E = Math.exp(-g * dt)
        this.x = E * (A * dt + B) + this.h
        this.v = -g * E * (A * dt + B) + A * E
      }
      else if (w0 > g) { // damping oscillation
        // x(t) = |z| exp(-g * t) sin(w * t + beta)
        const w = Math.sqrt(w0 * w0 - g * g)
        const ReZ = x0
        const ImZ = - (x0 * g + v0) / w
        const A = Math.sqrt(ReZ * ReZ + ImZ * ImZ)
        const E = Math.exp(-g * dt)
        const beta = Math.atan2(ReZ, -ImZ)
        this.x = A * E * Math.sin(w * dt + beta) + this.h
        this.v = A * E * (-g * Math.sin(w * dt + beta) + w * Math.cos(w * dt + beta))
      }
      else { // over damping
        // x(t) = A exp(lambda1 t) + B exp(lambda2 t)
        const d = Math.sqrt(g * g - w0 * w0)
        const l1 = -g + d
        const l2 = -g - d
        const A = (-l2 * x0 + v0) / (2 * d)
        const B = (l1 * x0 - v0) / (2 * d)
        this.x = A * Math.exp(l1 * dt) + B * Math.exp(l2 * dt) + this.h
        this.v = A * l1 * Math.exp(l1 * dt) + B * l2 * Math.exp(l2 * dt)
      }
    }
    else {
      // v = v0 * exp(-2 * g * t)
      // x = x0 + v0 / (2*g) * (1 - exp(-2 * g * t))
      const g0 = this.options.gamma0
      const v0 = this.v
      const E = Math.exp(-2 * g0 * dt)
      this.v = v0 * E
      this.x += v0 / (2 * g0) * (1 - E)
    }
    return this
  }

  get state() {
    const { x, v } = this
    const moving = Math.abs(v) >= this.options.minSpeed
    return { x, v, moving }
  }
}


class InertiaArray {
  private dim: Inertia[]

  constructor(n: number, options: Partial<Options> = {}) {
    options = { ...defaultOptions, ...options }
    this.dim = range(n).map(_ => new Inertia(options))
  }

  setOptions(options: Partial<Options>) {
    this.dim.forEach(i => i.setOptions(options))
    return this
  }

  evolve(dt: number) {
    this.dim.forEach(i => i.evolve(dt))
    return this
  }

  release() {
    this.dim.forEach(i => i.release())
    return this
  }

  protected _drag(dh: number[]) {
    this.dim.forEach((i, j) => i.drag(dh[j]))
    return this
  }

  protected _dragTo(h: number[]) {
    this.dim.forEach((i, j) => i.dragTo(h[j]))
    return this
  }

  stop() {
    this.dim.forEach(i => i.stop())
    return this
  }

  reset() {
    this.dim.forEach(i => i.reset())
    return this
  }

  protected get _state() {
    const ss = this.dim.map(i => i.state)
    return {
      x: ss.map(s => s.x),
      v: ss.map(s => s.v),
      moving: ss.some(s => s.moving),
    }
  }
}


export class Inertia2D extends InertiaArray {
  constructor(options: Partial<Options> = {}) {
    super(2, options)
  }

  drag(dx: number, dy: number) {
    return this._drag([dx, dy])
  }

  dragTo(x: number, y: number) {
    return this._dragTo([x, y])
  }

  get state() {
    const s = this._state
    return {
      position: { x: s.x[0], y: s.x[1] },
      velocity: { x: s.v[0], y: s.v[1] },
      moving: s.moving,
    }
  }
}


function range(n: number) {
  const a: number[] = []
  for (let i = 0; i < n; ++i) {
    a.push(i)
  }
  return a
}