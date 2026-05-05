// ここで export しているものは ./src/export.ts で型が矛盾していないかチェックする
import { Globe } from "@stellar-globe/stellar-globe"
import { CSSProperties, FC } from "react"
import { configureStore } from '@reduxjs/toolkit'

type AppProps = {
    hashSync?: boolean
    storageSync?: boolean
    catchAllKeyboardEvents?: boolean
    floatingLayerElement?: HTMLElement
    floatingLayerZIndex?: CSSProperties['zIndex']
    activeOnInit?: boolean
    storageKey?: string
    onStoreChange?: (e: StoreChangeEvent) => void
    initialState?: unknown
}

declare const App: FC<AppProps & { ref?: unknown }>
export default App


type AppState = any
type AppStateWithComputed = any

export function makeStore(args: {
    storageKey: string
    onStoreChange?: (e: StoreChangeEvent) => void
    initialState?: unknown
}): {
    dispatchAction: (action: any) => void,
    getState: () => AppStateWithComputed,
}

type StoreChangeEvent = {
    state: AppStateWithComputed
}

type AppHandle = {
    globe: () => Globe
    dispatchAction: (action: { type: string, payload: unknown }) => void
    getState: () => AppStateWithComputed,
    activate: () => void
    deactivate: () => void
}

export type { AppHandle, AppState }
