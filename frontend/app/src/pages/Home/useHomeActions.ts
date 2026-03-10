import { angle } from "@stellar-globe/stellar-globe"
import { useCallback } from "react"
import { homeSlice } from "../../store/features/homeSlice"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { useHomeContext, useResetView } from "./context"

export function useHomeActions() {
  const dispatch = useAppDispatch()
  const resetView = useResetView()
  const { globeHandle } = useHomeContext()
  const lineProfilerEnabled = useAppSelector(state => state.home.lineProfiler.enabled)

  const toggleLineProfiler = useCallback(() => {
    dispatch(homeSlice.actions.toggleLineProfiler())
  }, [dispatch])

  const rotateByDegrees = useCallback((degrees: number) => {
    const globe = globeHandle.current?.()
    if (!globe) {
      return
    }
    globe.camera.jumpTo({ roll: globe.camera.roll + angle.deg2rad(degrees) }, { duration: 400 })
  }, [globeHandle])

  const rotateClockwise = useCallback(() => {
    rotateByDegrees(90)
  }, [rotateByDegrees])

  const rotateCounterClockwise = useCallback(() => {
    rotateByDegrees(-90)
  }, [rotateByDegrees])

  const recenter = useCallback(() => {
    resetView()
  }, [resetView])

  return {
    lineProfilerEnabled,
    recenter,
    rotateClockwise,
    rotateCounterClockwise,
    toggleLineProfiler,
  }
}
