import styles from './styles.module.scss'
import { ClickableMarkerLayer$, MarkerLayer$ } from "@stellar-globe/react-stellar-globe"
import { Fragment, memo, useCallback, useMemo, useRef, useState } from "react"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { Catalog, Marker, catalogsSlice } from "./catalogSlice"
import { CSSTransition } from 'react-transition-group'
import { PointMarker } from '../../../common/stellarglobe/PointMarker'
import { V4 } from '@stellar-globe/stellar-globe'


export const CatalogLayers = memo(() => {
  const catalogs = useAppSelector(state => state.catalogs.catalogs)
  const focus = useAppSelector(state => state.catalogs.focusedPosition)
  const focusColor = useMemo<V4>(() => [1, 1, 1, 0.75], [])

  return (
    <Fragment>
      {catalogs.map(c => (
        <CatalogLayer$
          key={c.id}
          catalog={c}
        />
      ))}
      {focus &&
        <PointMarker
          color={focusColor}
          markerType='circledHollowPlus'
          position={focus}
          markerSize={64}
          markerWidth={0.05}
        />
      }
    </Fragment>
  )
})


type CatalogProps = {
  catalog: Catalog
}


const CatalogLayer$ = memo(({ catalog }: CatalogProps) => {
  const dispatch = useAppDispatch()

  type OnHoverChange = Parameters<typeof ClickableMarkerLayer$>[0]['onHoverChange']

  const [showObjectInspector, setShowObjectInspector] = useState(false)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)

  const onHoverChange = useCallback<NonNullable<OnHoverChange>>(({ index }) => {
    setShowObjectInspector(index !== null)
    if (index !== null) {
      setHoverIndex(index)
    }
  }, [])

  const nodeRef = useRef(null)

  const selectionColor: V4 = useMemo(() => [1, 1, 1, catalog.defaultColor[3]], [catalog.defaultColor])
  const white: V4 = useMemo(() => [1, 1, 1, 1], [])

  const selectionMarkers: Marker[] = useMemo(() => {
    const indices = Object.keys(catalog.selectedRecords)
    const markers: Marker[] = indices.map(i => ({
      position: catalog.markers[i as any].position,
    }))
    return markers
  }, [catalog.markers, catalog.selectedRecords])

  type OnClick = NonNullable<Parameters<typeof ClickableMarkerLayer$>[0]['onClick']>
  const onClick: OnClick = useCallback(e => {
    dispatch(catalogsSlice.actions.recordSelected({ id: catalog.id, index: e.index }))
  }, [catalog.id, dispatch])

  const selectedColor = useMemo<V4>(() => [1, 1, 1, 0.75], [])

  const showAttributes = useAppSelector(state => state.catalogs.showAttributes)

  return (
    <Fragment>
      <ClickableMarkerLayer$
        defaultColor={catalog.defaultColor}
        defaultType={catalog.defaultType}
        dimmAlpha={0.75}
        markers={catalog.markers}
        baseColor={catalog.baseColor}
        visible={catalog.visible}
        onHoverChange={onHoverChange}
        onClick={onClick}
      />
      <MarkerLayer$
        markerSize={64}
        markerWidth={0.05}
        defaultColor={selectedColor}
        defaultType="square"
        markers={selectionMarkers}
        baseColor={selectionColor}
        visible={catalog.visible}
      />
      {catalog.visible && showAttributes && (
        <CSSTransition
          in={showObjectInspector}
          timeout={{ enter: 0, exit: 200 }}
          nodeRef={nodeRef}
          mountOnEnter
          unmountOnExit
          classNames={{
            exit: styles.fadeExit,
            exitActive: styles.fadeExitActive,
          }}
        >
          {hoverIndex !== null && hoverIndex < catalog.attributes.length ? (
            <div ref={nodeRef} className={styles.objectInspector}>
              <table>
                <tbody>
                  {catalog.fields.map((field, fieldIndex) => (
                    <tr key={fieldIndex}>
                      <th>{field}</th>
                      <td>{catalog.attributes[hoverIndex][fieldIndex]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Fragment />}
        </CSSTransition>
      )}
    </Fragment>
  )
})
