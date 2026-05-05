import { useCallback } from "react"
import { useAppDispatch } from "../../store/hooks"
import { fitsImageSlice } from "./fitsImageSlice"

export function useAddFitsImageFile() {
  const dispatch = useAppDispatch()

  return useCallback((file: File) => {
    const url = URL.createObjectURL(file)
    const name = file.name
    dispatch(fitsImageSlice.actions.imageAdded({ name, url, hduIndex: 0, maskConfig: { color: [1, 0, 0, 1], maskBit: 1 } }))
  }, [dispatch])
}
