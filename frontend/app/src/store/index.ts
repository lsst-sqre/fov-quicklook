import { configureStore } from '@reduxjs/toolkit'
// import { homeSlice } from './features/homeSlice'
import { api } from './api'
import { SystemInfo } from './api/openapi'
import { copyTemplateInitialState, copyTemplateSlice } from './features/copyTemplateSlice'
import { hipsSlice } from './features/hipsSlice'
import { homeSlice } from './features/homeSlice'
import { systemSlice } from './features/systemSlice'

export function makeStore(systemInfo: SystemInfo) {
  return configureStore({
    reducer: {
      [systemSlice.name]: systemSlice.reducer,
      [homeSlice.name]: homeSlice.reducer,
      [copyTemplateSlice.name]: copyTemplateSlice.reducer,
      [hipsSlice.name]: hipsSlice.reducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware({
      serializableCheck: false,
    }).concat(api.middleware),
    preloadedState: {
      [copyTemplateSlice.name]: copyTemplateInitialState(systemInfo),
    },
  })
}

export type AppStore = ReturnType<typeof makeStore>
export type AppState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
