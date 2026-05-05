export function memoizeOne<T extends (...args: any[]) => any>(func: T): T {
  let lastArgs: any[] | null = null
  let lastResult: any

  return function (...args: Parameters<T>): ReturnType<T> {
    if (lastArgs !== null && args.length === lastArgs.length && args.every((arg, index) => Object.is(arg, lastArgs![index]))) {
      return lastResult
    }
    lastArgs = args
    lastResult = func(...args)
    return lastResult
  } as T
}
