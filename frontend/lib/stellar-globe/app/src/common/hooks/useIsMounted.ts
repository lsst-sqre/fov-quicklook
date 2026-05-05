import { useCallback, useEffect, useRef } from "react"

export function useIsMounted() {
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  return useCallback(() => {
    return mounted.current
  }, [])
}
