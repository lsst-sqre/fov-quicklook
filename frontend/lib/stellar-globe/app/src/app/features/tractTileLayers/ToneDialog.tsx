import { Fragment, Suspense, useCallback } from "react"
import { Icon } from "../../../common/components/Icon"
import { AppDialog } from "../../AppDialog"
import { useAppDispatch, useAppSelector } from "../../store/hooks"
import { ColorParamsControl } from "./ColorParamsControl"
import { compareFilterShortName, deferredFilterMap } from "./filtermap"
import { tractTileLayersSlice } from "./tractTileLayersSlice"
import { Loader } from "../../../common/components/Loader"
import { ErrorBoundary } from "react-error-boundary"


export function ToneDialog() {
  const visible = useAppSelector(state => state.tractTileLayers.toneDialogVisible)
  const dispatch = useAppDispatch()
  const toggle = useCallback(() => dispatch(tractTileLayersSlice.actions.toneDialogToggled({})), [dispatch])

  return (
    <Fragment>
      <AppDialog
        title={
          <Fragment>
            <Icon type="tune" marginRight />Tune
          </Fragment>
        }
        onCloseButtonClick={toggle}
        visible={visible}
      >
        <ErrorBoundary fallback={<Icon type="error" />}>
          <Suspense fallback={<Loader />}>
            <SafeColorParamsControl />
          </Suspense>
        </ErrorBoundary>
      </AppDialog>
    </Fragment>
  )
}


function SafeColorParamsControl() {
  const dispatch = useAppDispatch()
  const params = useAppSelector(state => state.tractTileLayers.colorParams)
  const shortNames = useFilterShortNames()

  return (
    <ColorParamsControl
      params={params}
      filterCandidates={shortNames}
      onChange={newParams => {
        dispatch(tractTileLayersSlice.actions.colorParamsUpdated({ params: newParams }))
      }}
    />
  )
}


function useFilterShortNames() {
  const activeLayers = useAppSelector(tractTileLayersSlice.selectors.activeLayers)
  const ds = activeLayers.map(layer => deferredFilterMap(layer.baseUrl))
  return [...new Set((function* () {
    for (const { promise, error, result } of ds) {
      if (result) {
        for (const s of result.map(f => f.commonName)) {
          yield s
        }
      }
      else {
        throw error ?? promise
      }
    }
  })()).values()].sort(compareFilterShortName)
}
