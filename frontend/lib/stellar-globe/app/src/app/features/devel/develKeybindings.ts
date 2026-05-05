import { enableWebglProfiler } from '@stellar-globe/stellar-globe'
import { useMemo, useRef } from "react"
import { Keybind } from "../../../common/components/keybindings"
import { useAppContext } from "../../context"
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { develSlice } from './develSlice'

export function useDevelKeybindings() {
  const profilerRef = useRef<ReturnType<typeof enableWebglProfiler>>()
  const { globeHandle } = useAppContext()
  const dispatch = useAppDispatch()
  const profilingSupported = useAppSelector(state => state.devel.profilerSupported)

  return useMemo(() => {
    const toggleProfiler: Keybind = {
      action: async () => {
        if (profilingSupported) {
          if (!profilerRef.current) {
            const gl = globeHandle.current!()!.gl
            const profiler = enableWebglProfiler(gl)
            profilerRef.current = profiler
            profiler.start()
            dispatch(develSlice.actions.profilerToggled({ active: true }))
          }
          else {
            await profilerRef.current!.stop()
            profilerRef.current.disable()
            profilerRef.current = undefined
            dispatch(develSlice.actions.profilerToggled({ active: false }))
          }
        }
      },
      shortcut: 'Meta+Ctrl+R',
    }

    return {
      toggleProfiler,
    }
  }, [dispatch, globeHandle, profilingSupported])
}
