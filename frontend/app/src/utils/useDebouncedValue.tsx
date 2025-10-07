import { useState, useEffect, useRef } from 'react'
import { Debounce } from './debounce'

export function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  const debouncerRef = useRef(Debounce(delay))

  useEffect(() => {
    throw new Error('useDebouncedValue: delay cannot be changed after the first render')
  }, [delay])

  useEffect(() => {
    debouncerRef.current(() => {
      setDebouncedValue(value)
    })

    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      debouncerRef.current!.stop()
    }
  }, [value])

  return debouncedValue
}
