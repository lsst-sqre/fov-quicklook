import { BeautifulObjectLayer$, ConstellationLayer$, EsoMilkyWayLayer$, Globe$, GlobeEventLayer$, GridLayer$, HipparcosCatalogLayer$, HipsSimpleLayer$, RollLayer$, TouchLayer$, ZoomLayer$ } from "@stellar-globe/react-stellar-globe"
import { GlobeEventMap } from "@stellar-globe/stellar-globe"
import { debounce } from "../common/utils/debounce"
import { useAppContext } from "./context"
import { TractFrameLayer$ } from "./features/appearanceLayers/RingsTract/TractFrameLayer"
import { TractNumbersLayer } from "./features/appearanceLayers/RingsTract/TractNumbersLayer"
import { cameraSlice } from "./features/camera/cameraSlice"
import { CatalogLayers } from "./features/catalog/CatalogLayers"
import { RegionsLayer } from "./features/regions/RegionsLayer"
import { ToolsLayer } from "./features/regions/ToolsLayer"
import { TractTileLayers } from "./features/tractTileLayers/TractTileLayers"
import { useAppDispatch, useAppSelector } from "./store/hooks"
import { ContextMenuLayer } from "./MainContextMenu/ContextMenuLayer"
import { MainContextMenu } from "./MainContextMenu"
import { FitsImageLayers } from "./features/fitsImage/FitsImageLayers"
import { useCallback } from "react"
import { indicatorSlice } from "./features/indicator/indicatorSlice"


export function MainViewer() {
  const dispatch = useAppDispatch()
  const { globeHandle } = useAppContext()

  const layers = useAppSelector(state => state.appearanceLayers)
  const camera = useAppSelector(state => state.camera)

  const onCameraMove = debounce(200, (e: GlobeEventMap['camera-move']) => {
    const { fovy, phi, roll, theta, za, zd, zp } = e.camera
    dispatch(cameraSlice.actions.paramsChanged({ fovy, phi, roll, theta, za, zd, zp }))
  })

  const onPointerMove = useCallback((e: GlobeEventMap['pointer-move']) => {
    dispatch(indicatorSlice.actions.mouseCoordUpdated([e.coord.a.rad, e.coord.d.rad]))
  }, [dispatch])

  const hips = useAppSelector(state => state.hipsLayers)

  return (
    <Globe$
      ref={globeHandle}
      projection={camera.projection}
      retina={camera.retina}
      cameraParams={camera.params}
      noDefaultLayers
      preserveBuffer
    >
      <GlobeEventLayer$ onCameraMove={onCameraMove} onPointerMove={onPointerMove} />
      <ZoomLayer$ />
      <RollLayer$ />
      <TouchLayer$ />
      <ContextMenuLayer render={(openedAt) => (
        <MainContextMenu openedAt={openedAt} />
      )} />

      <ToolsLayer>
        <BeautifulObjectLayer$ {...layers.nearbyGalaxiesAndNebulas} />

        {hips.baseUrl && <HipsSimpleLayer$ baseUrl={hips.baseUrl} />}
        <TractTileLayers />

        <EsoMilkyWayLayer$ {...layers.esoMilkyWay} />

        <HipparcosCatalogLayer$ {...layers.hipparcosCatalog} />
        <ConstellationLayer$ {...layers.constellation} />
        <GridLayer$ {...layers.grid} />

        <FitsImageLayers />

        <TractFrameLayer$ showPatch={layers.tracts.patch} visible={layers.tracts.visible} />
        {layers.tracts.visible &&
          <TractNumbersLayer />
        }
        <CatalogLayers />
        <RegionsLayer />
      </ToolsLayer>
    </Globe$>
  )
}
