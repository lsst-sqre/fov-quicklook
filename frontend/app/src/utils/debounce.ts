export function debounce<CB extends (...args: any[]) => void>(delay: number, cb: CB): CB {
  const d = Debounce(delay)
  const f = (...args: Parameters<CB>) => {
    d(() => {
      cb(...args)
    })
  }
  const { stop, skippedCalls } = d
  return Object.assign(f as CB, { stop, skippedCalls })
}

export function Debounce(delay: number) {
  let timer: undefined | ReturnType<typeof setTimeout> = undefined
  let skippedCalls = 0
  const f = (cb: () => void) => {
    if (timer) {
      clearTimeout(timer)
      ++skippedCalls
    }
    timer = setTimeout(() => {
      try {
        cb()
      }
      finally {
        timer = undefined
        skippedCalls = 0
      }
    }, delay)
  }
  return Object.assign(f, {
    stop: () => timer && clearTimeout(timer),
    skippedCalls: () => skippedCalls,
  })
}
