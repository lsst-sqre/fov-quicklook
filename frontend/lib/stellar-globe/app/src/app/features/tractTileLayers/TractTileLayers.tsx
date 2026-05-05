import { TractTileLayer$ } from "@stellar-globe/react-stellar-globe"
import { Fragment, Suspense, memo, useMemo } from "react"
import { ErrorBoundary } from "react-error-boundary"
import { useAppSelector } from "../../store/hooks"
import { useFilterMap } from "./filtermap"


export const TractTileLayers = memo(() => {
  const tractTilelayers = useAppSelector(state => state.tractTileLayers.layers)
  const params = useAppSelector(state => state.tractTileLayers.colorParams)
  const magFilter = useAppSelector(state => state.common.magFilter)

  return (
    <Fragment>
      {
        tractTilelayers.map(({ baseUrl, visible }) => (
          <ErrorBoundary key={baseUrl} fallback={<Fragment />}>
            <Suspense>
              <TractTileLayerWithFilterNameDictionary
                baseUrl={baseUrl}
                outline
                visible={visible}
                colorParams={params}
                magFilter={magFilter}
              />
            </Suspense>
          </ErrorBoundary>
        ))
      }
    </Fragment>
  )
})


function TractTileLayerWithFilterNameDictionary(props: Parameters<typeof TractTileLayer$>[0]) {
  const { baseUrl } = props
  const filterMap = useFilterMap(baseUrl)
  const filterNameDictionary = useMemo(
    () => Object.fromEntries(filterMap.map(({ intrinsicName, commonName }) => [commonName, intrinsicName])),
    [filterMap],
  )
  return <TractTileLayer$ filterNameDictionary={filterNameDictionary} {...props} />
}
