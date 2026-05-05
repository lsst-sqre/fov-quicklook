export function EventEmitter<T = void>({ once }: { once: boolean }) {
  const cbs: ((value: T) => void)[] = []

  const on = (cb: (value: T) => void) => {
    cbs.push(cb)
    return () => {
      const i = cbs.indexOf(cb)
      if (i >= 0) {
        cbs.splice(i, 1)
      }
    }
  }

  const emit = (value: T) => {
    if (once) {
      while (cbs.length > 0) {
        cbs.shift()!(value)
      }
    } else {
      for (const cb of cbs) {
        cb(value)
      }
    }
  }

  return {
    on,
    emit,
  }
}

export type EventEmitter<T = void> = ReturnType<typeof EventEmitter<T>>
