import { useRef } from "react"

export function useAssertCosnt<T>(value: T) {
  const memo = useRef(value)
  if (!Object.is(value, memo.current)) {
    throw new Error(`Const value changed: ${memo.current} -> ${value}`)
  }
}
