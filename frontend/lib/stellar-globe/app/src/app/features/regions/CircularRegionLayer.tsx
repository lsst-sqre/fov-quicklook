import { DomLayer$, PathLayer$, useLayerBind } from "@stellar-globe/react-stellar-globe"
import { Globe, GlobePointerDragEvent, Layer, SkyCoord, V2, V3, V4, glMatrix, makePointingObject } from "@stellar-globe/stellar-globe"
import { produce } from 'immer'
import { Fragment, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Icon } from "../../../common/components/Icon"
import { RegularMenu } from "../../../common/components/Menu/RegularMenu"
import { AngleUnit, formatAngle } from '../../../common/utils/formatAngle'
import { PointMarker } from "../../../common/stellarglobe/PointMarker"
import styles from './styles.module.scss'
const { vec3 } = glMatrix


export type CircleDef = {
  center: SkyCoord
  radius: number // radian
}

type Props = {
  circleDef: CircleDef
  color: V4
  angleUnit: AngleUnit
  onChange?: (circleDef: CircleDef) => void
  children?: ReactNode
  showLabel?: boolean
  onlyCenter?: boolean
  menuButton?: ReactNode
}

export const CircularRegionLayer = ({
  circleDef: circleDefProp,
  color,
  angleUnit,
  onChange,
  showLabel,
  children,
  onlyCenter = false,
  menuButton,
}: Props) => {
  type Paths = Parameters<typeof PathLayer$>[0]['paths']

  const [circleDef, setCircleDef] = useState(circleDefProp)

  useEffect(() => {
    setCircleDef(circleDefProp)
  }, [circleDefProp])

  const circumference = useMemo(() => Circumference(circleDef), [circleDef])

  const paths = useMemo(() => {
    const nDiv = 360
    const paths: Paths = [
      {
        close: true,
        joint: 'MITER',
        points: Array.from({ length: nDiv }, (_, i) => {
          const t = 2 * Math.PI * i / nDiv
          return {
            color,
            position: circumference(t),
            size: 0,
          }
        }),
      },
    ]
    return paths
  }, [circumference, color])

  const onSubmit = useCallback(() => {
    onChange?.(circleDef)
  }, [circleDef, onChange])

  const menuXyz = useMemo(() => circumference(Math.PI / 4), [circumference])
  const centerXyz = useMemo(() => circleDef.center.xyz, [circleDef.center.xyz])
  const offset = useMemo<V2>(() => [10, 10], [])

  const infoText = useMemo(() => (
    <Fragment>
      <Icon type='architecture' />
      {formatAngle(circleDef.radius, angleUnit)}
    </Fragment>
  ), [angleUnit, circleDef])

  return (
    <Fragment>
      {onlyCenter ||
        <PathLayer$
          paths={paths}
          blendMode="NORMAL"
          dimOnZoom={false}
          darkenNarrowLine={false}
        />
      }
      <PointMarker
        position={centerXyz}
        color={color}
        markerType="hollowPlus"
      />
      {showLabel && (
        <DomLayer$ position={menuXyz} offset={offset} >
          <RegularMenu
            renderMenuButton={() => (
              <div className={styles.lineInfo} >
                {menuButton ?? infoText}
                <Icon type="keyboard_arrow_down" />
              </div>
            )}
          >
            {children}
          </RegularMenu>
        </DomLayer$>
      )}
      {onChange && (
        <MouseLayer$ circleDef={circleDef} onChange={setCircleDef} onSubmit={onSubmit} />
      )}
    </Fragment>
  )
}


class MouseLayer extends Layer {
  constructor(
    globe: Globe,
    public props: MouseLayerProps,
  ) {
    super(globe)
    this.pointingObjects.push(
      circleCenterPointingObject(this),
      circumferencePointingObject(this),
    )
  }
}

function circleCenterPointingObject(layer: MouseLayer) {
  const globe = layer.globe
  return makePointingObject({
    hoverIcon: 'grab',
    dragIcon: 'grabbing',
    hit(e) {
      const { circleDef } = layer.props
      const hit = e.coord.angle(circleDef.center).rad <= 2.e-2 * globe.camera.fovy
      return {
        hit,
      }
    },
    onPointerDown(e) {
      const { circleDef } = layer.props
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(circleDef, _ => {
          _.center = e.coord
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



function circumferencePointingObject(layer: MouseLayer) {
  const globe = layer.globe
  return makePointingObject({
    hoverIcon: 'move',
    dragIcon: 'move',
    hit(e) {
      const { circleDef } = layer.props
      const hit = Math.abs(e.coord.angle(circleDef.center).rad - circleDef.radius) <= 2.e-2 * globe.camera.fovy
      return {
        hit,
      }
    },
    onPointerDown(e) {
      const { circleDef } = layer.props
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(circleDef, _ => {
          _.radius = e.coord.angle(circleDef.center).rad
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
  circleDef: CircleDef,
  onChange: (circleDef: CircleDef) => void
  onSubmit: () => void
}


function MouseLayer$({
  circleDef: circleDef,
  onChange,
  onSubmit,
}: MouseLayerProps) {
  const initialProps = useRef<MouseLayerProps>({ circleDef, onChange, onSubmit })
  const factory = useCallback((globe: Globe) => new MouseLayer(globe, { ...initialProps.current }), [])
  const { node, ifLayerReady } = useLayerBind<MouseLayer>(factory, true)
  const newProps = useMemo<MouseLayerProps>(() => ({ circleDef: circleDef, onChange, onSubmit }), [circleDef, onChange, onSubmit])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.props = newProps
    })
  }, [ifLayerReady, newProps])
  return node
}


function Circumference(circleDef: CircleDef) {
  const { center, radius } = circleDef
  const z = center.xyz
  const x = vec3.cross(vec3.create(), z, [0, 0, 1])
  vec3.normalize(x, x)
  const y = vec3.cross(vec3.create(), z, x)
  const u = radius
  return (t: number) => {
    const p = vec3.create()
    vec3.scaleAndAdd(p, p, z, Math.cos(u))
    vec3.scaleAndAdd(p, p, x, Math.sin(u) * Math.cos(t))
    vec3.scaleAndAdd(p, p, y, Math.sin(u) * Math.sin(t))
    return p as V3
  }
}
