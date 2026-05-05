type Options = {
  testDuration: number   // [ms]
  maxDecreasingRate: number // [1/s]
}

const defaults: Options = {
  testDuration: 200,
  maxDecreasingRate: 1.0,
}

export function realEventDetector(options: Partial<Options> = {}) {
  options = { ...defaults, ...options }
  const testDuration = options.testDuration!
  const maxDecreasingRate = options.maxDecreasingRate!
  const h = new RingBuffer<[number, number]>(Math.floor(testDuration / 16) + 4)

  return (e: WheelEvent) => {
    // * Events caused by inertial scrolling have a deltaY that decreases exponentially.
    // * Events are sent every 1/60 second at first, but when the deltaY is close to 1, events are sent every 1/30 second.
    // * We determine whether an event is an inertial event based on the history of deltaY.
    //   * We consider the event is inertial if in testDuration:
    //     * all deltaYs are in same sign.
    //     * On average, deltaY is decreasing decreasingRatio times per second.
    h.push([e.timeStamp, e.deltaY])
    let i
    for (i = 2; i <= h.length; ++i) {
      const [t, dy] = h.back(i)
      if (e.timeStamp - t <= testDuration) {
        if (e.deltaY * dy < 0) {
          return true
        }
      }
      else {
        break
      }
    }
    // テスト期間中に全部同じ符号の場合
    if (h.length < 2) {
      return true
    }
    const dt: number[] = []
    for (let j = 2; j < i; ++j) {
      dt.push(h.back(j - 1)[0] - h.back(j)[0])
    }
    const medDt = median(dt)
    if (Math.abs(e.deltaY) <= 1 && dt[0] > medDt * 1.05) {
      return false
    }
    const [t0, dy0] = h.back(i - 1)
    return Math.pow(e.deltaY / dy0, 1000 / (e.timeStamp - t0)) >= maxDecreasingRate
  }
}


function median(a: number[]) {
  // a.lengthが偶数
  // a[] = a[{0, 1, 2, 3}]
  // (a[1] + a[2]) / 2

  // a.lengthが奇数
  // a[] = a[{0, 1, 2, 3, 4}]
  // a[2]
  if ((a.length & 1) === 0) {
    // 偶数
    return (a[a.length >> 1] + a[(a.length >> 1) - 1]) / 2
  }
  else {
    return a[a.length >> 1]
  }
}


class RingBuffer<T> {
  private origin = 0
  private xs: T[] = []

  constructor(private readonly n: number) { }

  back(i: number): T {
    const j = (this.origin - i + this.xs.length) % this.xs.length
    return this.xs[j]
  }

  push(x: T) {
    if (this.xs.length < this.n) {
      this.xs.push(x)
    }
    else {
      this.xs[this.origin] = x
    }
    this.origin = (this.origin + 1) % this.n
  }

  get length() {
    return this.xs.length
  }
}
