export function memoize<F extends (...args: any[]) => any>(func: F): F {
  const cache = new Map<string, any>()

  return function (...args: any[]): any {
    const key = JSON.stringify(args)
    if (cache.has(key)) {
      return cache.get(key)
    }

    const result = func(...args)
    cache.set(key, result)
    return result
  } as F
}
