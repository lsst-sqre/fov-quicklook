import { useEffect, useState, useTransition } from "react"
import { useInstanceVariable } from "./useInstanceVaribale"
import { Debounce } from "../utils/debounce"

export function useDebounceInTransition<T>(delay: number, value: T): [T, boolean] {
  const debounce = useInstanceVariable(() => Debounce(delay))
  const [debounced, setDebounced] = useState(value)
  const [isPending, startTransition] = useTransition()
  useEffect(() => {
    debounce(() => {
      startTransition(() => {
        setDebounced(value)
      })
    })
  }, [debounce, value])
  return [debounced, isPending]
}
