// 実体のエクスポート

import { App } from "./app"
export default App

import { makeStoreForExport as makeStore } from "./app/store"
export { makeStore }

// 以下は型チェック用のコード
// ../types/index.d.ts と実装が矛盾しないかチェックする

import type { AppHandle } from './app'
import { AppState } from "./app/store"

import type {
  AppHandle as AppHandleType,
  AppState as AppStateType,
  makeStore as makeStoreType,
} from '../types'

type AssertTypeImplements<T, U extends T> = T
type _TypeCheck1 = AssertTypeImplements<AppHandleType, AppHandle>
type _TypeCheck2 = AssertTypeImplements<AppStateType, AppState>
type _TypeCheck3 = AssertTypeImplements<typeof makeStoreType, typeof makeStore>
