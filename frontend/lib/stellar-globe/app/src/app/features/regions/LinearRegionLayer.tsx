import { DomLayer$, PathLayer$, useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe, GlobePointerDragEvent, GlobePointerEvent, Layer, SkyCoord, V2, V3, V4, glMatrix, makePointingObject } from "@stellar-globe/stellar-globe"
import { produce } from 'immer'
import { Fragment, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Icon } from "../../../common/components/Icon"
import { RegularMenu } from "../../../common/components/Menu/RegularMenu"
import { AngleUnit, formatAngle } from '../../../common/utils/formatAngle'
import { slerp } from "../../../common/utils/math"
import styles from './styles.module.scss'
const { mat3, vec3, mat4 } = glMatrix


export type LineDef = {
  start: SkyCoord
  end: SkyCoord
}

type Props = {
  lineDef: LineDef
  color: V4
  angleUnit: AngleUnit
  onChange?: (lineDef: LineDef) => void
  children?: ReactNode
  showLabel?: boolean
}

export const LinearRegionLayer = ({
  lineDef: lineDefProp,
  color,
  angleUnit,
  onChange,
  children,
  showLabel,
}: Props) => {
  type Paths = Parameters<typeof PathLayer$>[0]['paths']

  const [lineDef, setLineDef] = useState(lineDefProp)

  useEffect(() => {
    setLineDef(lineDefProp)
  }, [lineDefProp])

  const paths = useMemo(() => {
    const { start, end } = lineDef
    const a = start
    const b = end
    const div = Math.floor(5 * a.angle(b).deg) + 1
    const paths: Paths = [
      {
        close: false,
        joint: 'MITER',
        points: Array.from({ length: div + 1 }, (_, i) => ({
          color,
          position: slerp(a.xyz, b.xyz, i / div),
          size: 0,
        })),
      },
    ]
    return paths
  }, [lineDef, color])

  const onSubmit = useCallback(() => {
    onChange?.(lineDef)
  }, [lineDef, onChange])

  const position = useMemo(() => lineDef.end.xyz, [lineDef.end])
  const offset = useMemo<V2>(() => [10, 10], [])
  const infoText = useMemo(() => (
    <Fragment>
      <Icon type="architecture" />
      {formatAngle(lineDef.start.angle(lineDef.end).rad, angleUnit)}
      <Icon type="keyboard_arrow_down" />
    </Fragment>
  ), [angleUnit, lineDef])

  return (
    <Fragment>
      <PathLayer$
        paths={paths}
        blendMode="NORMAL"
        dimOnZoom={false}
        darkenNarrowLine={false}
      />
      {showLabel &&
        <DomLayer$ position={position} offset={offset} >
          <RegularMenu
            renderMenuButton={() =>
              <div className={styles.lineInfo} >
                {infoText}
              </div>
            }
          >
            {children}
          </RegularMenu>
        </DomLayer$>
      }
      {onChange && (
        <MouseLayer$ lineDef={lineDef} onChange={setLineDef} onSubmit={onSubmit} />
      )}
    </Fragment>
  )
}
// setDisplayName({ LinearRegionLayer })


class MouseLayer extends Layer {
  constructor(
    globe: Globe,
    public props: MouseLayerProps,
  ) {
    super(globe)
    this.pointingObjects.push(
      lineEndsPointingObject(this),
      lineBodyPointingObject(this),
    )
  }
}


function lineBodyPointingObject(layer: MouseLayer) {
  const { globe } = layer
  const picker = makePointingObject({
    hoverIcon: 'grab',
    dragIcon: 'grabbing',
    hit(e: GlobePointerEvent) {
      const { start, end } = layer.props.lineDef
      const p = e.coord.xyz
      const a = start.xyz
      const b = end.xyz
      const c = vec3.normalize(vec3.create(), vec3.cross(vec3.create(), a, b))
      vec3.normalize(c, c)
      // @ts-ignore
      const A = mat3.fromValues(...a, ...b, ...c)
      if (mat3.determinant(A) === 0.) {
        return { hit: false, passThrough: false }
      }
      const B = mat3.invert(mat3.create(), A)
      const q = vec3.transformMat3(vec3.create(), p, B)
      const d = 1.e-2 * globe.camera.fovy
      const hit = q[0] >= 0 && q[1] >= 0 && Math.abs(q[2]) <= d
      return { hit, passThrough: false }
    },
    onPointerDown() {
      const baseLineDef = layer.props.lineDef
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(baseLineDef, _ => {
          const R = mat4.create()
          mat4.rotateZ(R, R, e.coord.a.rad)
          mat4.rotateY(R, R, -e.coord.d.rad + e.downEvent.coord.d.rad)
          mat4.rotateZ(R, R, -e.downEvent.coord.a.rad)
          const start = SkyCoord.fromXyz(vec3.transformMat4(vec3.create(), _.start.xyz, R) as V3)
          const end = SkyCoord.fromXyz(vec3.transformMat4(vec3.create(), _.end.xyz, R) as V3)
          _.start = start
          _.end = end
        })
        layer.props.onChange?.(newDef)
      }
      return {
        onDrag,
        onPointerUp: () => layer.props.onSubmit(),
      }
    }
  })
  return picker
}


function lineEndsPointingObject(layer: MouseLayer) {
  const globe = layer.globe
  return makePointingObject({
    hoverIcon: 'move',
    dragIcon: 'crosshair',
    hit(e) {
      const { lineDef } = layer.props
      const hit = (
        lineDef.start.angle(e.coord).rad <= 2.e-2 * globe.camera.fovy ||
        lineDef.end.angle(e.coord).rad <= 2.e-2 * globe.camera.fovy
      )
      return {
        hit,
      }
    },
    onPointerDown(e) {
      const { lineDef: baseLineDef } = layer.props
      const which = e.coord.cosine(baseLineDef.start) >= e.coord.cosine(baseLineDef.end) ? 'start' : 'end'
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(baseLineDef, _ => {
          _[which] = e.coord
        })
        return layer.props.onChange(newDef)
      }
      return {
        onDrag,
        onPointerUp: () => {
          layer.props.onSubmit()
        },
      }
    },
  })
}


type MouseLayerProps = {
  lineDef: LineDef,
  onChange: (lineDef: LineDef) => void
  onSubmit: () => void
}


function MouseLayer$({
  lineDef,
  onChange,
  onSubmit,
}: MouseLayerProps) {
  const initialProps = useRef<MouseLayerProps>({ lineDef, onChange, onSubmit })
  const factory = useCallback((globe: Globe) => new MouseLayer(globe, { ...initialProps.current }), [])
  const { node, ifLayerReady } = useLayerBind<MouseLayer>(factory, true)
  const newProps = useMemo<MouseLayerProps>(() => ({ lineDef, onChange, onSubmit }), [lineDef, onChange, onSubmit])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.props = newProps
    })
  }, [ifLayerReady, newProps])
  return node
}
