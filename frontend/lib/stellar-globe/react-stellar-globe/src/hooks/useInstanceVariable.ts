import { useMemo, useRef } from "react"

export function useInstanceVariable<T>(factory: () => T) {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const initialValue = useMemo(factory, [])
  const ref = useRef(initialValue)
  return ref.current
}
