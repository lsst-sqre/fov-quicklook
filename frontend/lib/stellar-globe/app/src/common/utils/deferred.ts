export function deferred<T, U>() {
  let resolve: (value: T) => void
  let reject: (value: U) => void
  const promise = new Promise<T>((_resolve, _reject) => {
    resolve = _resolve
    reject = _reject
  })
  return {
    promise,
    // @ts-ignore
    resolve,
    // @ts-ignore
    reject,
  }
}
