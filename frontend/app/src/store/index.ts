import { configureStore } from '@reduxjs/toolkit'
// import { homeSlice } from './features/homeSlice'
import { api } from './api'
import { homeSlice } from './features/homeSlice'
import { systemSlice } from './features/systemSlice'

export function makeStore() {
  return configureStore({
    reducer: {
      [systemSlice.name]: systemSlice.reducer,
      [homeSlice.name]: homeSlice.reducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(api.middleware),
  })
}

type Store = ReturnType<typeof makeStore>

export type RootState = ReturnType<Store['getState']>
export type AppDispatch = Store['dispatch']
