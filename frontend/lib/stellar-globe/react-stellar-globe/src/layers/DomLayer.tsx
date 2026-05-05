import { Globe, Layer, V2, V3, View, glMatrix } from "@stellar-globe/stellar-globe"
import { Fragment, ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useRef } from "react"
import { useGetGlobe, useLayerBind } from ".."
const { vec4 } = glMatrix


type Projected = {
  x: number
  y: number
  visible: boolean
}


type SharedState = {
  position: V3
  onProject: (projected: Projected) => void
}


class DomLayer extends Layer {
  constructor(globe: Globe, public shared: SharedState) {
    super(globe)
  }

  render(view: View): void {
    const clip = 1
    const p = vec4.transformMat4(vec4.create(), [...this.shared.position, 1], view.mvp.pv)
    const x = p[0] / p[3]
    const y = p[1] / p[3]
    const z = p[2] / p[3]
    const visible =
      -clip <= x && x <= clip &&
      -clip <= y && y <= clip &&
      -clip <= z && z <= clip
    this.shared.onProject({
      x, y,
      visible,
    })
  }
}


type Props = {
  children?: ReactNode
  offset?: V2
  visible?: boolean
  position: V3
}


export function DomLayer$({
  children,
  position,
  offset = [0, 0],
  visible = true,
}: Props) {
  const getGlobe = useGetGlobe()

  const onProject = useCallback(({ visible, x, y }: Projected) => {
    if (containerRef.current) {
      if (visible) {
        const globe = getGlobe()
        const { width, height } = (globe.gl.canvas as HTMLCanvasElement).getBoundingClientRect()
        const left = `${(width * (x + 1) / 2. + offset[0])}px`
        const top = `${(height * (1 - (y + 1) / 2.) + offset[1])}px`
        // const left = `${Math.round(width * (x + 1) / 2. + offset[0])}px`
        // const top = `${Math.round(height * (1 - (y + 1) / 2.) + offset[1])}px`
        const transform = `translateX(${left}) translateY(${top})`
        Object.assign(containerRef.current!.style, {
          display: 'block',
          left: 0,
          top: 0,
          transform,
        })
      }
      else {
        Object.assign(containerRef.current!.style, {
          display: 'none',
        })
      }
    }
  }, [getGlobe, offset])

  const shared = useRef<SharedState>({ position, onProject })
  const factory = useCallback((globe: Globe) => new DomLayer(globe, shared.current), [])
  const { node, ifLayerReady } = useLayerBind<DomLayer>(factory, visible)

  const newShared = useMemo<SharedState>(() => ({ position, onProject }), [onProject, position])
  useEffect(() => {
    ifLayerReady(layer => {
      layer.shared = newShared
      layer.globe.requestRefresh()
    })
  }, [ifLayerReady, newShared])

  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <Fragment>
      {node}
      <div ref={containerRef} style={{
        position: 'absolute',
      }}>
        {children}
      </div>
    </Fragment>
  )
}
