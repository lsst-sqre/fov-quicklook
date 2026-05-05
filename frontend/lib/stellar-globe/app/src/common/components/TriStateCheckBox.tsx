import { memo, useEffect, useRef } from "react"

export const TriStateCheckBox = memo(({ value, onChange }: { value: boolean | null; onChange: (value: boolean) => void} ) => {
  const nextValue = value === null ? true : !value
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (ref.current) {
      ref.current.indeterminate = value === null
    }
  }, [value])
  return <input ref={ref} type='checkbox' checked={value === true} onChange={() => onChange(nextValue)} />
})
