import { Action, ThunkAction, configureStore, createSlice } from "@reduxjs/toolkit"
import { makeGlobalStack } from "../../common/utils/globalstack"
import { appearanceLayersSlice } from "../features/appearanceLayers/appearanceLayersSlice"
import { cameraSlice } from "../features/camera/cameraSlice"
import { catalogsSlice } from "../features/catalog/catalogSlice"
import { commonSlice } from "../features/common/commonSlice"
import { develSlice } from "../features/devel/develSlice"
import { hipsLayersSlice } from "../features/hipsLayers/hipsLayersSlice"
import { regionsSlice } from "../features/regions/regionsSlice"
import { tractTileLayersSlice } from '../features/tractTileLayers/tractTileLayersSlice'
import { AppStateWithComputed, stateWithComputed } from "./computedState"
import { makeStateHistory } from "./stateHistory"
import { fitsImageSlice } from "../features/fitsImage/fitsImageSlice"
import { indicatorSlice } from "../features/indicator/indicatorSlice"


export function makeStore({
  storageKey,
  onStoreChange,
  initialState,
  activated = true,
  hashSync = true,
}: {
  storageKey: string
  hashSync?: boolean
  onStoreChange?: (e: StoreChangeEvent) => void
  initialState?: unknown // circular dependency を回避するためにunknown
  activated?: boolean
}) {
  const stateHistory = makeStateHistory()

  const store = storeInitializerParams.pushContext({ storageKey, hashSync }, () => {
    return configureStore({
      reducer: {
        [paramsSlice.name]: paramsSlice.reducer,
        [commonSlice.name]: commonSlice.reducer,
        [appearanceLayersSlice.name]: appearanceLayersSlice.reducer,
        [cameraSlice.name]: cameraSlice.reducer,
        [indicatorSlice.name]: indicatorSlice.reducer,
        [tractTileLayersSlice.name]: tractTileLayersSlice.reducer,
        [hipsLayersSlice.name]: hipsLayersSlice.reducer,
        [regionsSlice.name]: regionsSlice.reducer,
        [catalogsSlice.name]: catalogsSlice.reducer,
        [develSlice.name]: develSlice.reducer,
        [fitsImageSlice.name]: fitsImageSlice.reducer,
      },
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(
          stateHistory.middleware,
        ),
      preloadedState: initialState,
    })
  })

  store.dispatch(commonSlice.actions.activeChanged(activated))

  if (onStoreChange) {
    store.subscribe(() => {
      const state = store.getState()
      onStoreChange({ state: stateWithComputed(state) })
    })
  }

  return {
    store,
    stateHistory,
  }
}


export function makeStoreForExport(params: Parameters<typeof makeStore>[0]) {
  const { store } = makeStore(params)
  return {
    getState: () => stateWithComputed(store.getState()),
    dispatchAction: store.dispatch,
  }
}


export type StoreChangeEvent = {
  state: AppStateWithComputed
}

export type AppStore = ReturnType<typeof makeStore>['store']
export type AppDispatch = AppStore['dispatch']
export type AppState = ReturnType<AppStore['getState']>
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  AppState,
  unknown,
  Action<string>
>


export const storeInitializerParams = makeGlobalStack<{
  storageKey: string
  hashSync: boolean
}>()


const paramsSlice = createSlice({
  name: 'initializerParams',
  initialState: storeInitializerParams.current,
  reducers: {},
})
