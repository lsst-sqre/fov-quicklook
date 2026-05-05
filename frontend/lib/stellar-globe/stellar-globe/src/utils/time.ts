export function time(name: string, cb: () => void) {
  const start = performance.now()
  const result = cb()
  console.log(`${name}: ${performance.now() - start}`)
  return result
}

export function sleep(t = 0) {
  return new Promise((resolve) => setTimeout(resolve, t))
}

export const waitIdleTime = (() => {
  let q: Array<() => void> = []
  let rafId: undefined | number

  const consumeOne = () => {
    rafId = requestAnimationFrame(() => {
      rafId = undefined
      if (q.length > 0) {
        q.shift()!()
        consumeOne()
      }
    })
  }
  
  return () => new Promise<void>((resolve) => {
    q.push(resolve)
    if (rafId === undefined) {
      consumeOne()
    }
  })
})()
