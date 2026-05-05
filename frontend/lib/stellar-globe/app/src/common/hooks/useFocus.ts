import { RefObject, useEffect, useState } from "react"


export function useIsFocused(ref: RefObject<HTMLElement>, deps: unknown[] = []) {
  const [isFocused, setIsFocused] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (el) {
      const onFocus = () => {
        setIsFocused(true)
      }
      const onBlur = () => {
        setIsFocused(false)
      }
      el.addEventListener('focus', onFocus)
      el.addEventListener('blur', onBlur)
      return () => {
        el.removeEventListener('blur', onBlur)
        el.removeEventListener('focus', onFocus)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ref, ...deps])

  return isFocused
}
