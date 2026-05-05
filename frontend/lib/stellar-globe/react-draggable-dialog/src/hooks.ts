import { useRef } from 'react'

export function useInstanceVariable<T>(make: () => T) {
  const ref = useRef<{ initialized: boolean; value?: T} >({ initialized: false })
  if (!ref.current.initialized) {
    ref.current = { initialized: true, value: make() }
  }
  return ref.current.value!
}

const seq = (() => {
  let id = 0
  return () => {
    return ++id
  }
})()

export function useSeqId() {
  return useInstanceVariable(seq)
}
