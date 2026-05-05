import { useRef } from "react"

export function useInstanceVariable<T>(make: () => T) {
  const ref = useRef<{ initialized: false } | { initialized: true, value: T }>({ initialized: false })
  if (!ref.current.initialized) {
    ref.current = {
      initialized: true,
      value: make(),
    }
  }
  return ref.current.value
}
