import { useCallback } from "react"
import { useAppDispatch } from "../../store/hooks"
import { regionsSlice } from "./regionsSlice"


const $type = 'hscMap5/regions'


export const useImportRegionJson = Object.assign(() => {
  const dispatch = useAppDispatch()
  return useCallback((json: any) => {
    const { $type: _$type, $content } = json
    if (_$type !== $type) {
      throw new Error(`Invalid file schema: ${_$type}`)
    }
    dispatch(regionsSlice.actions.regionsImported({ regions: $content }))
  }, [dispatch])
}, { $type })
