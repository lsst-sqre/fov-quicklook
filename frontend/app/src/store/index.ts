import { configureStore } from '@reduxjs/toolkit'
// import { homeSlice } from './features/homeSlice'
import { api } from './api'
import { copyTemplateSlice } from './features/copyTemplateSlice'
import { hipsSlice } from './features/hipsSlice'
import { homeSlice } from './features/homeSlice'
import { systemSlice } from './features/systemSlice'

export function makeStore() {
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
  })
}

export type AppStore = ReturnType<typeof makeStore>
export type AppState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
