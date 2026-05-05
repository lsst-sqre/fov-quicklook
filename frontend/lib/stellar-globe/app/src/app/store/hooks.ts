import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux"
import type { AppState, AppDispatch } from "."
import { makeStateHistoryActions } from "./stateHistory"

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch: () => AppDispatch = useDispatch
export const useAppSelector: TypedUseSelectorHook<AppState> = useSelector
export const appStateHistoryActions = makeStateHistoryActions<AppState>()
