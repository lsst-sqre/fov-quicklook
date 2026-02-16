import { configureStore } from '@reduxjs/toolkit'
import { api } from './api'
import { SystemInfo } from './api/openapi'
import { copyTemplateInitialState, copyTemplateSlice } from './features/copyTemplateSlice'
import { homeInitialState, homeSlice } from './features/homeSlice'

export function makeStore(systemInfo: SystemInfo) {
  return configureStore({
    reducer: {
      [homeSlice.name]: homeSlice.reducer,
      [copyTemplateSlice.name]: copyTemplateSlice.reducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware({
      serializableCheck: false,
    }).concat(api.middleware),
    preloadedState: {
      [homeSlice.name]: homeInitialState(systemInfo),
      [copyTemplateSlice.name]: copyTemplateInitialState(systemInfo),
    },
  })
}

export type AppStore = ReturnType<typeof makeStore>
export type AppState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
