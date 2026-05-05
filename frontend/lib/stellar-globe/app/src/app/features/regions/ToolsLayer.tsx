import { PanLayer$ } from '@stellar-globe/react-stellar-globe'
import { GlobePointerDragEvent, GlobePointerEvent, SkyCoord, V4 } from '@stellar-globe/stellar-globe'
import { Fragment, ReactNode, memo, useCallback, useMemo, useState } from 'react'
import { setDisplayName } from '../../../common/utils/setDisplayName'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { CircularRegionLayer } from './CircularRegionLayer'
import { LinearRegionLayer } from './LinearRegionLayer'
import { PointerLayer$ } from '../../../common/stellarglobe/PointerLayer'
import { RectDef, RectangularRegionLayer } from './RectangularRegionLayer'
import { normalizeSkyCoord } from './regionUtils'
import { regionsSlice } from './regionsSlice'


export function ToolsLayer({ children }: { children: ReactNode }) {
  const tool = useAppSelector(state => state.regions.tool)

  return (
    <Fragment>
      <PanLayer$ enabled={tool === 'pan'} />
      {children}
      {tool === 'line' && <NewLinearRegionLayer />}
      {tool === 'circle' && <NewCircularRegionLayer />}
      {tool === 'rect' && <NewRectangularRegionLayer />}
      {tool === 'text' && <NewTextRegionLayer />}
    </Fragment>
  )
}


type NewTwoPointsRegionLayerProps = {
  render: (coords: [SkyCoord, SkyCoord]) => ReactNode
  onSubmit: (coords: [SkyCoord, SkyCoord]) => void
}


function NewTwoPointsRegionLayer({ render, onSubmit }: NewTwoPointsRegionLayerProps) {
  const [coords, setCoords] = useState<[SkyCoord, SkyCoord] | null>(null)

  const onDrag = useCallback((e: GlobePointerDragEvent) => {
    setCoords([e.downEvent.coord, e.coord])
  }, [])

  const onUp = useCallback((e: GlobePointerDragEvent) => {
    if (e.moved) {
      onSubmit([e.downEvent.coord, e.coord])
    }
    setCoords(null)
  }, [onSubmit])

  return (
    <Fragment>
      {coords && render(coords)}
      <PointerLayer$ onDrag={onDrag} onUp={onUp} hoverIcon='crosshair' dragIcon='crosshair' />
    </Fragment>
  )
}


const NewLinearRegionLayer = memo(() => {
  const toolPinned = useAppSelector(state => state.regions.toolPinned)
  const dispatch = useAppDispatch()

  const addRegion = useCallback((coords: [SkyCoord, SkyCoord]) => {
    const [start, end] = coords
    dispatch(regionsSlice.actions.newLinearRegionAdded({
      type: 'Linear',
      start: normalizeSkyCoord(start),
      end: normalizeSkyCoord(end),
      visible: true,
      showLabel: true,
      name: '',
    }))
    if (!toolPinned) {
      dispatch(regionsSlice.actions.toolChanged({ tool: 'pan' }))
    }
  }, [dispatch, toolPinned])

  const color = useMemo<V4>(() => [1, 0, 1, 1], [])
  const lineDef = (coords: [SkyCoord, SkyCoord]) => ({ start: coords[0], end: coords[1] })
  const angleUnit = useAppSelector(state => state.common.angleUnit)

  return (
    <NewTwoPointsRegionLayer
      onSubmit={addRegion}
      render={coords => (
        <LinearRegionLayer
          lineDef={lineDef(coords)}
          color={color}
          angleUnit={angleUnit}
          showLabel
        />
      )}
    />
  )
})
setDisplayName({ NewLinearRegionLayer })


const NewCircularRegionLayer = memo(() => {
  const toolPinned = useAppSelector(state => state.regions.toolPinned)
  const dispatch = useAppDispatch()

  const addRegion = useCallback((coords: [SkyCoord, SkyCoord]) => {
    const [a, b] = coords
    dispatch(regionsSlice.actions.newCircularRegionAdded({
      type: 'Circular',
      center: normalizeSkyCoord(a),
      radius: a.angle(b).rad,
      visible: true,
      showLabel: true,
      name: '',
    }))
    if (!toolPinned) {
      dispatch(regionsSlice.actions.toolChanged({ tool: 'pan' }))
    }
  }, [dispatch, toolPinned])

  const color = useMemo<V4>(() => [1, 0, 1, 1], [])
  const circleDef = (coords: [SkyCoord, SkyCoord]) => ({ center: coords[0], radius: coords[0].angle(coords[1]).rad })
  const angleUnit = useAppSelector(state => state.common.angleUnit)

  return (
    <NewTwoPointsRegionLayer
      onSubmit={addRegion}
      render={coords => (
        <CircularRegionLayer
          circleDef={circleDef(coords)}
          color={color}
          angleUnit={angleUnit}
          showLabel
        />
      )}
    />
  )
})
setDisplayName({ NewCircularRegionLayer })


const NewRectangularRegionLayer = memo(() => {
  const toolPinned = useAppSelector(state => state.regions.toolPinned)
  const dispatch = useAppDispatch()

  const addRegion = useCallback((coords: [SkyCoord, SkyCoord]) => {
    const [a, b] = coords
    dispatch(regionsSlice.actions.newRectangularRegionAdded({
      type: 'Rectangular',
      minRa: a.a.rad,
      maxRa: b.a.rad,
      minDec: a.d.rad,
      maxDec: b.d.rad,
      visible: true,
      showLabel: true,
      name: '',
    }))
    if (!toolPinned) {
      dispatch(regionsSlice.actions.toolChanged({ tool: 'pan' }))
    }
  }, [dispatch, toolPinned])

  const color = useMemo<V4>(() => [1, 0, 1, 1], [])
  const rectDef = (coords: [SkyCoord, SkyCoord]): RectDef => ({
    minRa: coords[0].a.rad,
    maxRa: coords[1].a.rad,
    minDec: coords[0].d.rad,
    maxDec: coords[1].d.rad,
  })
  const angleUnit = useAppSelector(state => state.common.angleUnit)

  return (
    <NewTwoPointsRegionLayer
      onSubmit={addRegion}
      render={coords => (
        <RectangularRegionLayer
          rectDef={rectDef(coords)}
          color={color}
          angleUnit={angleUnit}
          showLabel
        />
      )}
    />
  )
})
setDisplayName({ NewRectangularRegionLayer })




const NewTextRegionLayer = memo(() => {
  const toolPinned = useAppSelector(state => state.regions.toolPinned)
  const dispatch = useAppDispatch()

  const addRegion = useCallback((coord: SkyCoord) => {
    dispatch(regionsSlice.actions.newTextRegionAdded({
      type: 'Text',
      position: normalizeSkyCoord(coord),
      name: 'Edit me...',
      visible: true,
      showLabel: true,
    }))
    if (!toolPinned) {
      dispatch(regionsSlice.actions.toolChanged({ tool: 'pan' }))
    }
  }, [dispatch, toolPinned])

  const onClick = useCallback((e: GlobePointerEvent) => {
    addRegion(e.coord)
  }, [addRegion])

  return (
    <PointerLayer$ onClick={onClick} hoverIcon='crosshair' dragIcon='crosshair' />
  )
})
setDisplayName({ NewTextRegionLayer })
