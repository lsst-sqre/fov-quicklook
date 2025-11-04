import { useEffect, useRef } from "react"

export function useWatch<T>(watchedValue: T, callback: (before: T, after: T) => void) {
  const previousValue = useRef<T>(watchedValue)
  const isFirstRender = useRef(true)

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }

    if (previousValue.current !== watchedValue) {
      callback(previousValue.current, watchedValue)
      previousValue.current = watchedValue
    }
  }, [watchedValue, callback])
}
