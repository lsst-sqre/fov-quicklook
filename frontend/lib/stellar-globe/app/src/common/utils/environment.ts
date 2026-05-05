export const detectEnvironment = (() => {
  let memoizedResult: 'browser' | 'node' | 'unknown' | undefined

  return (): 'browser' | 'node' | 'unknown' => {
    if (memoizedResult) {
      return memoizedResult
    }

    if (typeof window !== 'undefined' && typeof window.document !== 'undefined') {
      memoizedResult = 'browser'
    } else if (typeof process !== 'undefined' && process.versions != null && process.versions.node != null) {
      memoizedResult = 'node'
    } else {
      memoizedResult = 'unknown'
    }

    return memoizedResult
  }
})()
