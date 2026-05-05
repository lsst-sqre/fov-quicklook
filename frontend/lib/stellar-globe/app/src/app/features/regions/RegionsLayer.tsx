import { PathLayer$ } from "@stellar-globe/react-stellar-globe"
import { V4 } from "@stellar-globe/stellar-globe"
import { FocusableItem, MenuItem } from "@szhsin/react-menu"
import { Fragment, memo, useCallback, useMemo } from "react"
import { ColorPickerRgba } from "../../../common/components/ColorPicker"
import { Icon } from "../../../common/components/Icon"
import { setDisplayName } from "../../../common/utils/setDisplayName"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { CircleDef, CircularRegionLayer } from "./CircularRegionLayer"
import { LineDef, LinearRegionLayer } from "./LinearRegionLayer"
import { RectDef, RectangularRegionLayer } from "./RectangularRegionLayer"
import { normalizeSkyCoord, skyCoordFromCoordDef } from "./regionUtils"
import { regionsSlice } from "./regionsSlice"


export function RegionsLayer() {
  const regions = useAppSelector(state => state.regions.regions)

  return (
    <Fragment>
      {regions.filter(r => r.visible).map((def) => {
        switch (def.type) {
          case 'Linear':
            return <LinearRegionFromDefLayer key={def.id} {...def} />
          case 'Circular':
            return <CircularRegionFromDefLayer key={def.id} {...def} />
          case 'Rectangular':
            return <RectangularRegionFromDefLayer key={def.id} {...def} />
          case 'Text':
            return <TextRegionFromDefLayer key={def.id} {...def} />
          case 'Path':
            return <PathRegionFromDefLayer key={def.id} {...def} />
        }
      })}
    </Fragment>
  )
}


type RegionDef = ReturnType<typeof regionsSlice['getInitialState']>['regions'][number]
type SpecificRegionType<U extends RegionDef['type'], T = RegionDef> = T extends { type: U } ? T : never


const LinearRegionFromDefLayer = memo(({
  id,
  start,
  end,
  color,
  visible,
  showLabel,
  name,
}: SpecificRegionType<'Linear'>) => {
  const dispatch = useAppDispatch()

  const original = useMemo(() => ({
    id,
    start,
    end,
    color,
    visible,
    showLabel,
    name,
  }), [color, end, id, name, showLabel, start, visible])

  const onLineDefChange = useCallback((e: LineDef) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Linear',
        ...original,
        start: normalizeSkyCoord(e.start),
        end: normalizeSkyCoord(e.end),
      },
    }))
  }, [dispatch, id, original])

  const onColorChange = useCallback((color: V4) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Linear',
        ...original,
        color,
      },
    }))
  }, [dispatch, id, original])

  const lineDef = useMemo(() => ({
    start: skyCoordFromCoordDef(start),
    end: skyCoordFromCoordDef(end),
  }), [end, start])

  const duplicate = useCallback(() => {
    dispatch(regionsSlice.actions.newLinearRegionAdded({
      type: 'Linear',
      start,
      end,
      visible: true,
      showLabel,
      name,
    }))
  }, [dispatch, end, name, showLabel, start])

  return (
    <LinearRegionLayer
      lineDef={lineDef}
      color={color}
      angleUnit={useAppSelector(state => state.common.angleUnit)}
      onChange={onLineDefChange}
      showLabel={showLabel}
    >
      <MenuItem onClick={duplicate}><Icon type='content_copy' marginRight />Duplicate</MenuItem>
      <ColorPicker color={color} onChange={onColorChange} />
      <MenuItem
        onClick={() => {
          dispatch(regionsSlice.actions.regionDeleted({ id }))
        }}
      ><Icon type="delete" marginRight />Delete</MenuItem>
    </LinearRegionLayer>)
})
setDisplayName({ LinearRegionFromDefLayer })


type ColorPickerProps = {
  color: V4
  onChange: (color: V4) => void
}


const ColorPicker = memo(({ color, onChange }: ColorPickerProps) => {
  return (
    <FocusableItem>{
      () => (
        <Fragment>
          <Icon type="palette" marginRight />
          <ColorPickerRgba color={color} onChange={onChange} />
        </Fragment>
      )}
    </FocusableItem>
  )
})


const CircularRegionFromDefLayer = memo(({
  id,
  center,
  radius,
  color,
  visible,
  showLabel,
  name,
}: SpecificRegionType<'Circular'>) => {
  const dispatch = useAppDispatch()

  const original = useMemo(() => ({
    id,
    center,
    radius,
    color,
    visible,
    showLabel,
    name,
  }), [center, color, id, name, radius, showLabel, visible])

  const onCircleDefChange = useCallback((e: CircleDef) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Circular',
        ...original,
        center: normalizeSkyCoord(e.center),
        radius: e.radius,
      },
    }))
  }, [dispatch, id, original])

  const onColorChange = useCallback((color: V4) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Circular',
        ...original,
        color,
      },
    }))
  }, [dispatch, id, original])

  const circleDef = useMemo(() => ({
    center: skyCoordFromCoordDef(center),
    radius: radius,
  }), [center, radius])

  const duplicate = useCallback(() => {
    dispatch(regionsSlice.actions.newCircularRegionAdded({
      type: 'Circular',
      center,
      radius,
      name,
      visible: true,
      showLabel: true,
    }))
  }, [center, dispatch, name, radius])

  return (
    <CircularRegionLayer
      circleDef={circleDef}
      color={color}
      angleUnit={useAppSelector(state => state.common.angleUnit)}
      onChange={onCircleDefChange}
      showLabel={showLabel}
    >
      <MenuItem onClick={duplicate}><Icon type='content_copy' marginRight />Duplicate</MenuItem>
      <ColorPicker color={color} onChange={onColorChange} />
      <MenuItem
        onClick={() => {
          dispatch(regionsSlice.actions.regionDeleted({ id }))
        }}
      ><Icon type="delete" marginRight />Delete</MenuItem>
    </CircularRegionLayer>
  )
})
setDisplayName({ CircularRegionFromDefLayer })


const RectangularRegionFromDefLayer = memo(({
  id,
  minRa,
  maxRa,
  minDec,
  maxDec,
  color,
  visible,
  showLabel,
  name,
}: SpecificRegionType<'Rectangular'>) => {
  const dispatch = useAppDispatch()

  const original = useMemo(() => ({
    id,
    minRa,
    maxRa,
    minDec,
    maxDec,
    color,
    visible,
    showLabel,
    name,
  }), [color, id, maxDec, maxRa, minDec, minRa, name, showLabel, visible])

  const onRectDefChange = useCallback(({ minRa, maxRa, minDec, maxDec }: RectDef) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Rectangular',
        ...original,
        minRa, maxRa, minDec, maxDec,
      },
    }))
  }, [dispatch, id, original])


  const onColorChange = useCallback((color: V4) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Rectangular',
        ...original,
        color,
      },
    }))
  }, [dispatch, id, original])

  const rectDef = useMemo(() => ({
    minRa,
    maxRa,
    minDec,
    maxDec,
  }), [maxDec, maxRa, minDec, minRa])

  const duplicate = useCallback(() => {
    dispatch(regionsSlice.actions.newRectangularRegionAdded({
      type: 'Rectangular',
      name,
      minRa,
      maxRa,
      maxDec,
      minDec,
      visible: true,
      showLabel: true,
    }))
  }, [dispatch, maxDec, maxRa, minDec, minRa, name])

  return (
    <RectangularRegionLayer
      rectDef={rectDef}
      color={color}
      angleUnit={useAppSelector(state => state.common.angleUnit)}
      onChange={onRectDefChange}
      showLabel={showLabel}
    >
      <MenuItem onClick={duplicate}><Icon type='content_copy' marginRight />Duplicate</MenuItem>
      <MenuItem
        onClick={() => {
          dispatch(regionsSlice.actions.regionDeleted({ id }))
        }}
      ><Icon type="delete" marginRight />Delete</MenuItem>
      <ColorPicker color={color} onChange={onColorChange} />
    </RectangularRegionLayer>
  )
})
setDisplayName({ CircularRegionFromDefLayer })


const TextRegionFromDefLayer = memo(({
  id,
  position,
  name,
  color,
  visible,
  showLabel,
}: SpecificRegionType<'Text'>) => {
  const dispatch = useAppDispatch()

  const original = useMemo(() => ({
    id,
    position,
    name,
    color,
    visible,
    showLabel,
  }), [color, id, name, position, showLabel, visible])

  const onCircleDefChange = useCallback((e: CircleDef) => {
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Text',
        ...original,
        position: normalizeSkyCoord(e.center),
      },
    }))
  }, [dispatch, id, original])

  type RegionDef = Partial<Parameters<typeof regionsSlice.actions.regionUpdated>[0]['regionDef']>

  const onChange = useCallback(({ name, color }: { name?: string, color?: V4 }) => {
    const overwrite: RegionDef = { type: 'Text' }
    if (name !== undefined) {
      overwrite.name = name
    }
    if (color) {
      overwrite.color = color
    }
    dispatch(regionsSlice.actions.regionUpdated({
      id,
      regionDef: {
        type: 'Text',
        ...original,
        ...overwrite,
      },
    }))
  }, [dispatch, id, original])

  const circleDef = useMemo(() => ({
    center: skyCoordFromCoordDef(position),
    radius: 0,
  }), [position])

  const duplicate = useCallback(() => {
    dispatch(regionsSlice.actions.newTextRegionAdded({
      type: 'Text',
      position,
      name,
      visible: true,
      showLabel: true,
    }))
  }, [dispatch, name, position])

  return (
    <CircularRegionLayer
      onlyCenter
      circleDef={circleDef}
      color={color}
      angleUnit={useAppSelector(state => state.common.angleUnit)}
      onChange={onCircleDefChange}
      showLabel={showLabel}
      menuButton={<span style={{ color: v4ToColorString(color) }}>{baseName(name)}</span>}
    >
      <FocusableItem>
        {({ ref }) => (
          <input ref={ref} type='text' value={name} onChange={e => onChange({ name: e.currentTarget.value })} />
        )}
      </FocusableItem>
      <MenuItem onClick={duplicate}><Icon type='content_copy' marginRight />Duplicate</MenuItem>
      <ColorPicker color={color} onChange={color => onChange({ color })} />
      <MenuItem
        onClick={() => {
          dispatch(regionsSlice.actions.regionDeleted({ id }))
        }}
      ><Icon type="delete" marginRight />Delete</MenuItem>
    </CircularRegionLayer>
  )
})
setDisplayName({ TextRegionFromDefLayer })


function baseName(path: string) {
  return path.split('/').splice(-1)[0]
}


function v4ToColorString(color: V4) {
  const [r, g, b, a] = color
  return `rgba(${Math.round(255 * r)}, ${Math.round(255 * g)}, ${Math.round(255 * b)}, ${a})`
}


const PathRegionFromDefLayer = memo(({
  // color,
  // id,
  // name,
  paths,
  // showLabel,
  // type,
  visible,
}: SpecificRegionType<'Path'>) => {

  return (
    <PathLayer$
      paths={paths}
      darkenNarrowLine={false}
      dimOnZoom={false}
      visible={visible}
      blendMode="NORMAL"
    />
  )
})
setDisplayName({ PathRegionFromDefLayer })
