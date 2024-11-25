import { SkyCoord, V2 } from "@stellar-globe/stellar-globe"
import { memo, useEffect, useMemo, useRef } from "react"
import { useGlobe, useHomeContext } from "../context"

// import { useCrvalOriginWcs } from "../hooks"
import { useAppSelector } from "../../../store/hooks"
import { useWcs } from "../hooks"
import { WebglPlot, WebglPlotProps } from "./WebglPlot"


export const LineProfiler = memo(() => {
  const { quicklookHandle } = useHomeContext()
  const globe = useGlobe()
  const [, mouseY] = useAppSelector(state => state.home.mouseCursorClientCoord)
  const camera = useAppSelector(state => state.home.viewerCamera)
  const wcs = useWcs()
  const quicklookLayer = quicklookHandle.current?.layer()

  const chartData: WebglPlotProps | undefined = useMemo(() => {
    // eslint-disable-next-line @typescript-eslint/no-unused-expressions
    camera // cameraの移動でも再計算される必要がある
    if (globe && wcs && quicklookLayer) {
      const { x: minX, width } = globe.containerElement.getBoundingClientRect()
      const n = width << 0
      const xy = new Float32Array(n * 2)
      let max = -Infinity
      let min = Infinity
      // const x: number[] = []
      // const y: number[] = []
      for (let i = 0; i < n; ++i) {
        const m: V2 = [minX + (i / (n - 1)) * width, mouseY]
        const skyCoord: SkyCoord = globe.canvas.coordFromClientCoord({ clientX: m[0], clientY: m[1] })
        const pixelCoords = wcs.xyz2pixel(skyCoord.xyz)
        const { value } = quicklookLayer.pixelValue(pixelCoords) ?? [-1, Number.NaN]
        xy[i * 2] = i
        xy[i * 2 + 1] = value
        if (value > max) max = value
        if (value < min) min = value
        // x.push(i)
        // y.push(value)
      }
      return { xy, min, max }
    }
  }, [camera, globe, wcs, quicklookLayer, mouseY])

  const containerRef = useRef<HTMLDivElement>(null)
  const chartSize = useRef<{ width: number; height: number }>()

  useEffect(() => {
    const { width, height } = containerRef.current!.getBoundingClientRect()
    chartSize.current = { width, height }
  })

  return (
    <div style={{ height: '200px', width: '100%' }} ref={containerRef}>
      {chartData && chartSize.current && <WebglPlot {...chartData} />}
    </div>
  )
})
