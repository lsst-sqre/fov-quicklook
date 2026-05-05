export function EventManager<EventMap>() {
  type Keys = keyof EventMap

  const events: Map<Keys, Set<(event: any) => void>> = new Map()

  const on = <K extends Keys>(type: K, cb: (e: EventMap[K]) => void) => {
    if (!events.has(type)) {
      events.set(type, new Set())
    }
    events.get(type)!.add(cb)
    return () => {
      events.get(type)?.delete(cb)
    }
  }

  const emit = <K extends Keys>(type: K, event: EventMap[K]) => {
    for (const cb of events.get(type) ?? []) {
      cb(event)
    }
  }

  return {
    on,
    emit,
  }
}


type CallbackQueueOptions = {
  runReversedOrder?: boolean
}


function CallbackQueue({
  runReversedOrder = false,
}: CallbackQueueOptions = {}) {
  const cbs: (() => void)[] = []
  const add = (cb: () => void) => {
    cbs.push(cb)
    return () => {
      const i = cbs.indexOf(cb)
      if (i >= 0) {
        cbs.splice(i, 1)
      }
    }
  }
  const flush = () => {
    const getFirst = runReversedOrder ? (() => cbs.pop()) : (() => cbs.shift())
    while (cbs.length > 0) {
      getFirst()!()
    }
  }
  return {
    add,
    flush,
  }
}


export function ReleaseCallbacks() {
  return CallbackQueue({ runReversedOrder: true })
}
