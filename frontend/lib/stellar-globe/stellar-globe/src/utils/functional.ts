export function throttle(delay: number, cb: () => void) {
  let timer: ReturnType<typeof setTimeout> | undefined
  const f = () => {
    if (timer === undefined) {
      timer = setTimeout(() => {
        timer = undefined
        cb()
      }, delay)
    }
  }
  return f
}

export function debounce(delay: number, cb: () => void) {
  let timer: ReturnType<typeof setTimeout> | undefined
  const f = () => {
    if (timer !== undefined) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      timer = undefined
      cb()
    }, delay)
  }
  return f
}
