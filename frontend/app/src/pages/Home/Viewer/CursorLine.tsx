import { useState, useEffect } from "react"
import { useAppSelector } from "../../../store/hooks"
import { useGlobe } from "../context"

export function CursorLine() {
  const [, mouseY] = useAppSelector(state => state.home.mouseCursorClientCoord)
  const showLineProfiler = useAppSelector(state => state.home.lineProfiler.enabled)
  const globeHandle = useGlobe()
  const [offset, setOffset] = useState<[number, number]>()

  useEffect(() => {
    if (globeHandle?.canvas.domElement) {
      const rect = globeHandle.canvas.domElement.getBoundingClientRect()
      setOffset([rect.left, rect.top])
    }
  }, [globeHandle?.canvas.domElement])

  return (
    showLineProfiler && offset && (
      <div
        style={{
          position: 'absolute',
          top: `${mouseY - offset[1]}px`,
          left: 0,
          right: 0,
          height: 1,
          backgroundColor: 'rgba(255, 0, 0, 1)',
          pointerEvents: 'none',
        }} />
    )
  )
}
