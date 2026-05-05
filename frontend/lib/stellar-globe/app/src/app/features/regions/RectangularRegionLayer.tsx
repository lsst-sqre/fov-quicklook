import { DomLayer$, PathLayer$, useLayerBind } from "@stellar-globe/react-stellar-globe"
import { CursorStyle, Globe, GlobePointerDragEvent, GlobePointerEvent, Layer, SkyCoord, V2, V3, V4, makePointingObject } from "@stellar-globe/stellar-globe"
import { produce } from 'immer'
import { Fragment, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Icon } from "../../../common/components/Icon"
import { RegularMenu } from "../../../common/components/Menu/RegularMenu"
import { AngleUnit, formatAngle } from "../../../common/utils/formatAngle"
import { memoizeOne } from "../../../common/utils/memoizeOne"
import { PointMarker } from '../../../common/stellarglobe/PointMarker'
import styles from './styles.module.scss'


export type RectDef = {
  minRa: number
  maxRa: number
  minDec: number
  maxDec: number
}


type Props = {
  rectDef: RectDef
  color: V4
  angleUnit: AngleUnit
  onChange?: (rectDef: RectDef) => void
  showLabel?: boolean
  children?: ReactNode
}

export const RectangularRegionLayer = ({
  rectDef: rectDefProp,
  color,
  angleUnit,
  onChange,
  showLabel,
  children,
}: Props) => {
  type Paths = Parameters<typeof PathLayer$>[0]['paths']

  const [rectDef, setRawRectDef] = useState(() => normalizeRectDef(rectDefProp))

  const setRectDef = useCallback((rectDef: RectDef) => {
    setRawRectDef(normalizeRectDef(rectDef))
  }, [])

  useEffect(() => {
    setRectDef(rectDefProp)
  }, [rectDefProp, setRectDef])

  const paths = useMemo(() => {
    const { minRa, maxRa, minDec, maxDec } = rectDef
    const a: V2 = [minRa, minDec]
    const b: V2 = [maxRa, minDec]
    const c: V2 = [maxRa, maxDec]
    const d: V2 = [minRa, maxDec]
    const paths: Paths = [
      {
        close: true,
        joint: 'MITER',
        points: [
          /*
           *  D--C
           *  |  |
           *  A--B
           * 
           */
          ...[[a, b], [b, c], [c, d], [d, a]].map(([p, q]) => {
            const div = Math.floor(180 / Math.PI * Math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2)) + 1
            return Array.from({ length: div }, (_, i) => {
              const t = i / div
              const u = 1 - t
              return {
                color,
                size: 0,
                position: SkyCoord.fromRad(u * p[0] + t * q[0], u * p[1] + t * q[1]).xyz,
              }
            })
          }),
        ].flat(),
      },
    ]
    return paths
  }, [color, rectDef])

  const onSubmit = useCallback(() => {
    onChange?.(normalizeRectDef(rectDef))
  }, [rectDef, onChange])

  const offset = useMemo<V2>(() => [10, 10], [])
  const menuXyz = useMemo(() => SkyCoord.fromRad(Math.min(rectDef.minRa, rectDef.maxRa), rectDef.minDec).xyz, [rectDef])
  const centerXyz = useMemo<V3>(() => rectCenterNoMemo(rectDef).xyz, [rectDef])

  const infoText = useMemo(() => {
    const { maxDec, minDec, maxRa, minRa } = rectDef
    const height = maxDec - minDec
    const width = Math.cos((maxDec + minDec) / 2) * (maxRa - minRa)
    return (
      <Fragment>
        <Icon type='height' />
        {formatAngle(height, angleUnit)}
        <Icon type='arrow_range' marginLeft />
        {formatAngle(width, angleUnit)}
      </Fragment>
    )
  }, [angleUnit, rectDef])

  return (
    <Fragment>
      <PathLayer$
        paths={paths}
        blendMode="NORMAL"
        dimOnZoom={false}
        darkenNarrowLine={false}
      />
      <PointMarker
        color={color}
        position={centerXyz}
        markerType='diamond'
      />
      {showLabel &&
        <DomLayer$ position={menuXyz} offset={offset} >
          <RegularMenu
            renderMenuButton={() => (
              <div className={styles.lineInfo} >
                {infoText}
                <Icon type="keyboard_arrow_down" />
              </div>
            )}
          >
            {children}
          </RegularMenu>
        </DomLayer$>
      }
      {onChange && (
        <MouseLayer$ rectDef={rectDef} onChange={setRectDef} onSubmit={onSubmit} />
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
      rectCenterPointingObject(this),
      rectEdgePointingObject(this),
    )
  }
}


function rectCenterPointingObject(layer: MouseLayer) {
  const globe = layer.globe
  const rectCenter = memoizeOne(rectCenterNoMemo)

  return makePointingObject({
    hoverIcon: 'grab',
    dragIcon: 'grabbing',
    hit(e) {
      const { rectDef } = layer.props
      const hit = e.coord.angle(rectCenter(rectDef)).rad <= 2.e-2 * globe.camera.fovy
      return {
        hit,
      }
    },
    onPointerDown() {
      const epsilon = 1.e-2 * globe.camera.fovy
      const { rectDef } = layer.props
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(rectDef, _ => {
          const dA = e.coord.a.rad - e.downEvent.coord.a.rad
          const dD = e.coord.d.rad - e.downEvent.coord.d.rad
          _.minRa += dA
          _.maxRa += dA
          _.minDec = Math.max(-Math.PI / 2 + epsilon, Math.min(Math.PI / 2 - epsilon, _.minDec + dD))
          _.maxDec = Math.max(-Math.PI / 2 + epsilon, Math.min(Math.PI / 2 - epsilon, _.maxDec + dD))
        })
        return layer.props.onChange(normalizeRectDef(newDef))
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



function rectEdgePointingObject(layer: MouseLayer) {
  type EdgeType = 'minRa' | 'maxRa' | 'minDec' | 'maxDec'
  const globe = layer.globe

  const margin = () => 2.e-2 * globe.camera.fovy

  const raInRange = ({ coord: { a } }: GlobePointerEvent) => {
    // ra=360 を跨いでいる場合は minRa > 2 pi > maxRa となっている
    // その場合の条件は maxRa <= ra < 2 pi || 0 <= ra < minRa - 2 pi
    const { rectDef } = layer.props
    const { minRa, maxRa } = rectDef
    return minRa > 2 * Math.PI ?
      maxRa <= a.rad || a.rad < minRa - 2 * Math.PI
      :
      minRa <= a.rad + margin() && a.rad - margin() <= maxRa
  }
  const decInRange = ({ coord: { d } }: GlobePointerEvent) =>
    layer.props.rectDef.minDec <= d.rad + margin() && d.rad - margin() <= layer.props.rectDef.maxDec
  const raDiff = ({ coord: { a } }: GlobePointerEvent, which: 'minRa' | 'maxRa') =>
    Math.abs(fmod2pi(layer.props.rectDef[which]) - a.rad)
  const raAround = (e: GlobePointerEvent, which: 'minRa' | 'maxRa') =>
    raDiff(e, which) <= margin()
  const decDiff = ({ coord: { d } }: GlobePointerEvent, which: 'minDec' | 'maxDec') =>
    Math.abs(layer.props.rectDef[which] - d.rad)
  const decAround = (e: GlobePointerEvent, which: 'minDec' | 'maxDec') =>
    decDiff(e, which) <= margin()

  const hits = {
    minRa: memoizeOne((e: GlobePointerEvent) => decInRange(e) && raAround(e, 'minRa')),
    maxRa: memoizeOne((e: GlobePointerEvent) => decInRange(e) && raAround(e, 'maxRa')),
    minDec: memoizeOne((e: GlobePointerEvent) => raInRange(e) && decAround(e, 'minDec')),
    maxDec: memoizeOne((e: GlobePointerEvent) => raInRange(e) && decAround(e, 'maxDec')),
  } as const

  const checkHits = (e: GlobePointerEvent) => {
    const h = Object.fromEntries((Object.keys(hits) as EdgeType[]).map(k => [k, hits[k](e)])) as Record<EdgeType, boolean>
    if (h.minRa && h.maxRa) {
      if (raDiff(e, 'minRa') < raDiff(e, 'maxRa')) {
        h.maxRa = false
      } else {
        h.minRa = false
      }
    }
    if (h.minDec && h.maxDec) {
      if (decDiff(e, 'minDec') < decDiff(e, 'maxDec')) {
        h.maxDec = false
      } else {
        h.minDec = false
      }
    }
    return h
  }

  const icon = (e: GlobePointerEvent): CursorStyle => {
    const h = checkHits(e)
    const flip = layer.props.rectDef.minRa > 2 * Math.PI
    return (
      h.minRa && h.minDec && (flip ? 'nesw-resize' : 'nwse-resize') ||
      h.minRa && h.maxDec && (flip ? 'nwse-resize' : 'nesw-resize') ||
      h.maxRa && h.minDec && (flip ? 'nwse-resize' : 'nesw-resize') ||
      h.maxRa && h.maxDec && (flip ? 'nesw-resize' : 'nwse-resize') ||
      (h.minRa || h.maxRa) && 'ew-resize' ||
      (h.minDec || h.maxDec) && 'ns-resize' || 'not-allowed'
    )
  }

  return makePointingObject({
    hoverIcon: icon,
    dragIcon: icon,
    hit(e) {
      return {
        hit: hits.minRa(e) || hits.maxRa(e) || hits.minDec(e) || hits.maxDec(e)
      }
    },
    onPointerDown(downEvent) {
      const altKey = downEvent.originalEvent({
        mouse: e => e.altKey,
        touch: e => e.altKey,
      })
      const { rectDef } = layer.props
      const h = checkHits(downEvent)
      const w = {
        minRa: 'a', maxRa: 'a',
        minDec: 'd', maxDec: 'd',
      } as const
      const onDrag = (e: GlobePointerDragEvent) => {
        const newDef = produce(rectDef, _ => {
          if (altKey) {
            if (h.minRa || h.maxRa) {
              const midA = (_.minRa + _.maxRa) / 2
              const dA = e.coord.a.rad - midA
              _.minRa = midA - dA
              _.maxRa = midA + dA
            }
            if (h.maxDec || h.minDec) {
              const midD = (_.minDec + _.maxDec) / 2
              const dD = e.coord.d.rad - midD
              _.minDec = midD - dD
              _.maxDec = midD + dD
            }
          }
          else {
            for (const k of ['minRa', 'maxRa', 'minDec', 'maxDec'] as const) {
              if (h[k]) {
                _[k] = e.coord[w[k]].rad
              }
            }
          }
        })
        return layer.props.onChange(normalizeRectDef(newDef))
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
  rectDef: RectDef,
  onChange: (rectDef: RectDef) => void
  onSubmit: () => void
}


function MouseLayer$({
  rectDef,
  onChange,
  onSubmit,
}: MouseLayerProps) {
  const initialProps = useRef<MouseLayerProps>({ rectDef, onChange, onSubmit })
  const factory = useCallback((globe: Globe) => new MouseLayer(globe, { ...initialProps.current }), [])
  const { node, ifLayerReady } = useLayerBind<MouseLayer>(factory, true)
  const newProps = useMemo<MouseLayerProps>(() => ({ rectDef, onChange, onSubmit }), [rectDef, onChange, onSubmit])

  useEffect(() => {
    ifLayerReady(layer => {
      layer.props = newProps
    })
  }, [ifLayerReady, newProps])
  return node
}


function normalizeRectDef(rectDef: RectDef) {
  return produce(rectDef, _ => {
    _.minRa = fmod2pi(_.minRa)
    _.maxRa = fmod2pi(_.maxRa)
    if (_.maxRa < _.minRa) {
      [_.maxRa, _.minRa] = [_.minRa, _.maxRa]
    }
    if (_.maxDec < _.minDec) {
      [_.maxDec, _.minDec] = [_.minDec, _.maxDec]
    }
    if (_.maxRa - _.minRa > Math.PI) {
      _.minRa += 2 * Math.PI
    }
  })
}


function fmod2pi(a: number) {
  if (a < 0) {
    return (2 * Math.PI) - (-a % (2 * Math.PI))
  }
  return a % (2 * Math.PI)
}


function rectCenterNoMemo(rectDef: RectDef) {
  const { minRa, maxRa, minDec, maxDec } = rectDef
  return SkyCoord.fromRad((minRa + maxRa) / 2, (minDec + maxDec) / 2)
}
