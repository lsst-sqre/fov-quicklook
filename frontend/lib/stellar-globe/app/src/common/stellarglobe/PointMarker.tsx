import { MarkerLayer$ } from "@stellar-globe/react-stellar-globe"
import { V3, V4 } from "@stellar-globe/stellar-globe"
import { memo, useMemo } from "react"


type PointMarkerProps = {
  position: V3
  color: V4
  markerType: Parameters<typeof MarkerLayer$>[0]['defaultType']
  markerSize?: number
  markerWidth?: number
  visible?: boolean
}


export const PointMarker = memo(({
  position,
  color,
  markerType,
  markerSize,
  markerWidth,
  visible,
}: PointMarkerProps) => {
  type Marker = Parameters<typeof MarkerLayer$>[0]['markers'][number]

  const markers = useMemo<Marker[]>(() => [{
    position,
  }], [position])

  const defaultColor = useMemo<V4>(() => [1, 1, 1, 1], [])

  return (
    <MarkerLayer$
      baseColor={color}
      markers={markers}
      markerSize={markerSize}
      markerWidth={markerWidth}
      defaultColor={defaultColor}
      defaultType={markerType}
      visible={visible}
    />
  )
})
